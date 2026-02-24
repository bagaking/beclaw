#!/usr/bin/env python3
"""Feishu -> LongRun bridge daemon for Lobster Shell v0."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import textwrap
import threading
import urllib.error
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dirs(root: Path) -> dict[str, Path]:
    shell_root = root / ".bagakit" / "lobster-shell"
    paths = {
        "shell_root": shell_root,
        "state_dir": shell_root / "state",
        "logs_dir": shell_root / "logs",
        "outbox_dir": shell_root / "outbox",
        "runtime_dir": shell_root / "runtime",
        "db": shell_root / "state" / "dedup.sqlite",
        "results": shell_root / "outbox" / "results.jsonl",
        "identity": shell_root / "identity.md",
        "ralph_msg": root / ".bagakit" / "long-run" / "ralph-msg.md",
        "run_once": root / ".bagakit" / "lobster-shell" / "scripts" / "run_once.sh",
        "living_search": root / ".codex" / "skills" / "bagakit-living-docs" / "scripts" / "living-docs-memory.sh",
        "memory_inbox": root / "docs" / ".bagakit" / "inbox",
    }
    for key in ("state_dir", "logs_dir", "outbox_dir", "runtime_dir"):
        paths[key].mkdir(parents=True, exist_ok=True)
    paths["ralph_msg"].parent.mkdir(parents=True, exist_ok=True)
    if not paths["ralph_msg"].exists():
        paths["ralph_msg"].write_text("", encoding="utf-8")
    return paths


def init_db(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_messages (
              msg_id TEXT PRIMARY KEY,
              received_at TEXT NOT NULL,
              source TEXT NOT NULL,
              chat_id TEXT,
              user_id TEXT,
              payload_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def parse_text_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, dict):
        if "text" in content:
            return str(content.get("text") or "")
        return json.dumps(content, ensure_ascii=False)
    text = str(content)
    if not text.strip():
        return ""
    try:
        maybe = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(maybe, dict) and "text" in maybe:
        return str(maybe.get("text") or "")
    return text


def normalize_payload(payload: dict[str, Any]) -> dict[str, str] | None:
    if payload.get("type") == "url_verification" and payload.get("challenge"):
        return None

    event = payload.get("event") if isinstance(payload.get("event"), dict) else payload
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}

    msg_id = (
        message.get("message_id")
        or payload.get("message_id")
        or payload.get("msg_id")
        or event.get("msg_id")
        or ""
    )
    chat_id = message.get("chat_id") or event.get("chat_id") or payload.get("chat_id") or ""

    sender_id = ""
    sender_id_obj = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
    sender_id = sender_id_obj.get("user_id") or sender.get("user_id") or payload.get("user_id") or ""

    text = (
        parse_text_content(message.get("content"))
        or parse_text_content(payload.get("content"))
        or str(payload.get("text") or "")
        or str(event.get("text") or "")
    ).strip()

    if not msg_id:
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        msg_id = f"hash-{digest[:24]}"

    if not text:
        return {
            "msg_id": str(msg_id),
            "chat_id": str(chat_id),
            "user_id": str(sender_id),
            "text": "",
            "source": "feishu",
        }

    return {
        "msg_id": str(msg_id),
        "chat_id": str(chat_id),
        "user_id": str(sender_id),
        "text": text,
        "source": "feishu",
    }


def save_processed(paths: dict[str, Path], message: dict[str, str], payload: dict[str, Any]) -> bool:
    """Return False when duplicate."""
    with sqlite3.connect(paths["db"]) as conn:
        try:
            conn.execute(
                """
                INSERT INTO processed_messages (msg_id, received_at, source, chat_id, user_id, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message["msg_id"],
                    utc_now_iso(),
                    message["source"],
                    message.get("chat_id", ""),
                    message.get("user_id", ""),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def recall_memory(paths: dict[str, Path], root: Path, query: str, max_results: int) -> str:
    script = paths["living_search"]
    if not script.exists():
        return "(living-docs search script not found)"
    cmd = [
        "bash",
        str(script),
        "search",
        query,
        "--root",
        str(root),
        "--max-results",
        str(max_results),
        "--snippets",
    ]
    cp = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    if cp.returncode != 0:
        stderr = cp.stderr.strip() or "unknown error"
        return f"(memory recall failed: {stderr})"
    out = cp.stdout.strip()
    return out if out else "(no relevant memory found)"


def build_injected_message(paths: dict[str, Path], normalized: dict[str, str], recall: str, run_id: str) -> str:
    identity = ""
    if paths["identity"].exists():
        identity = paths["identity"].read_text(encoding="utf-8").strip()

    lines = [
        "# Lobster Shell Injection",
        "",
        "## Identity",
        identity or "(identity file missing)",
        "",
        "## Context Recall",
        recall,
        "",
        "## Inbound Message",
        normalized["text"],
        "",
        "## Envelope",
        f"- run_id: {run_id}",
        f"- source: {normalized['source']}",
        f"- msg_id: {normalized['msg_id']}",
        f"- chat_id: {normalized.get('chat_id', '') or '-'}",
        f"- user_id: {normalized.get('user_id', '') or '-'}",
        f"- received_at: {utc_now_iso()}",
    ]
    return "\n".join(lines).strip() + "\n"


def append_to_ralph_msg(msg_file: Path, segment: str) -> None:
    existing = msg_file.read_text(encoding="utf-8") if msg_file.exists() else ""
    if existing.strip():
        merged = existing.rstrip() + "\n\n---\n\n" + segment
    else:
        merged = segment
    msg_file.write_text(merged, encoding="utf-8")


def run_once(paths: dict[str, Path], root: Path, run_id: str) -> dict[str, Any]:
    run_script = paths["run_once"]
    if not run_script.exists():
        return {
            "status": "failed",
            "reason": f"missing run_once script: {run_script}",
            "exit_code": 1,
            "run_id": run_id,
        }

    cp = subprocess.run(
        ["bash", str(run_script), "--root", str(root), "--run-id", run_id],
        cwd=root,
        capture_output=True,
        text=True,
    )

    payload: dict[str, Any] = {
        "status": "failed" if cp.returncode else "completed",
        "exit_code": cp.returncode,
        "run_id": run_id,
        "stdout": cp.stdout.strip(),
        "stderr": cp.stderr.strip(),
    }

    if cp.stdout.strip():
        last_line = cp.stdout.strip().splitlines()[-1]
        try:
            obj = json.loads(last_line)
            if isinstance(obj, dict):
                payload.update(obj)
        except json.JSONDecodeError:
            pass

    return payload


def write_memory_note(paths: dict[str, Path], normalized: dict[str, str], run_result: dict[str, Any], run_id: str) -> str:
    inbox_dir = paths["memory_inbox"]
    if not inbox_dir.is_dir():
        return ""

    note_path = inbox_dir / f"howto-lobster-shell-{run_id}.md"
    content = textwrap.dedent(
        f"""
        ---
        title: Lobster shell run {run_id}
        required: false
        sop: Read when debugging lobster-shell dispatch runs.
        status: inbox
        ---

        ## Input
        - msg_id: {normalized['msg_id']}
        - chat_id: {normalized.get('chat_id', '') or '-'}
        - user_id: {normalized.get('user_id', '') or '-'}
        - text: {normalized['text']}

        ## Run Result
        - status: {run_result.get('status', 'unknown')}
        - exit_code: {run_result.get('exit_code', -1)}
        - run_log: {run_result.get('run_log', '-')}

        ## Next
        - Review run logs and decide whether to promote to durable memory.
        """
    ).strip() + "\n"
    note_path.write_text(content, encoding="utf-8")
    return str(note_path)


def append_outbox(paths: dict[str, Path], payload: dict[str, Any]) -> None:
    with paths["results"].open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def post_callback(url: str, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return f"ok:{resp.status}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return f"error:{exc}"


def process_payload(
    root: Path,
    paths: dict[str, Path],
    payload: dict[str, Any],
    memory_max_results: int,
    callback_url: str,
) -> tuple[dict[str, Any], int]:
    if payload.get("type") == "url_verification" and payload.get("challenge"):
        return {"challenge": payload.get("challenge")}, HTTPStatus.OK

    normalized = normalize_payload(payload)
    if normalized is None:
        return {"status": "ignored", "reason": "non-message event"}, HTTPStatus.OK

    if not normalized["text"]:
        return {
            "status": "ignored",
            "reason": "empty_text",
            "msg_id": normalized["msg_id"],
        }, HTTPStatus.OK

    accepted = save_processed(paths, normalized, payload)
    if not accepted:
        return {
            "status": "duplicate",
            "msg_id": normalized["msg_id"],
        }, HTTPStatus.OK

    run_id = f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{normalized['msg_id'][:8]}"
    recall = recall_memory(paths, root, normalized["text"], memory_max_results)
    injected = build_injected_message(paths, normalized, recall, run_id)
    append_to_ralph_msg(paths["ralph_msg"], injected)

    run_result = run_once(paths, root, run_id)
    note_path = write_memory_note(paths, normalized, run_result, run_id)

    result_payload: dict[str, Any] = {
        "timestamp": utc_now_iso(),
        "run_id": run_id,
        "msg_id": normalized["msg_id"],
        "chat_id": normalized.get("chat_id", ""),
        "user_id": normalized.get("user_id", ""),
        "status": run_result.get("status", "unknown"),
        "exit_code": int(run_result.get("exit_code", -1)),
        "run_log": run_result.get("run_log", ""),
        "memory_note": note_path,
    }
    append_outbox(paths, result_payload)

    callback_status = "skipped"
    if callback_url.strip():
        callback_status = post_callback(callback_url.strip(), result_payload)
    result_payload["callback_status"] = callback_status

    status_code = HTTPStatus.OK if result_payload["exit_code"] == 0 else HTTPStatus.INTERNAL_SERVER_ERROR
    return result_payload, status_code


class LobsterHTTPHandler(BaseHTTPRequestHandler):
    root: Path
    paths: dict[str, Path]
    secret: str
    memory_max_results: int
    callback_url: str
    lock: threading.Lock

    def _write_json(self, payload: dict[str, Any], status: int) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/healthz":
            self._write_json({"status": "ok", "time": utc_now_iso()}, HTTPStatus.OK)
            return
        self._write_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/feishu/event":
            self._write_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return

        if self.secret:
            token = self.headers.get("X-Lobster-Token", "")
            if token != self.secret:
                self._write_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
                return

        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_json({"error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
            return

        with self.lock:
            resp, status = process_payload(
                root=self.root,
                paths=self.paths,
                payload=payload,
                memory_max_results=self.memory_max_results,
                callback_url=self.callback_url,
            )
        self._write_json(resp, status)

    def log_message(self, fmt: str, *args: Any) -> None:
        # Keep daemon quiet unless explicitly needed.
        return


def run_server(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = ensure_dirs(root)
    init_db(paths["db"])

    class _Handler(LobsterHTTPHandler):
        pass

    _Handler.root = root
    _Handler.paths = paths
    _Handler.secret = args.secret.strip()
    _Handler.memory_max_results = int(args.memory_max_results)
    _Handler.callback_url = args.callback_url
    _Handler.lock = threading.Lock()

    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    print(f"listening=http://{args.host}:{args.port}/feishu/event")
    print(f"health=http://{args.host}:{args.port}/healthz")
    print(f"root={root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def run_self_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    paths = ensure_dirs(root)
    init_db(paths["db"])

    required = [
        root / ".bagakit" / "long-run" / "ralphloop-runner.sh",
        root / ".bagakit" / "lobster-shell" / "identity.md",
        root / ".bagakit" / "lobster-shell" / "scripts" / "run_once.sh",
        root / ".codex" / "skills" / "bagakit-living-docs" / "scripts" / "living-docs-memory.sh",
    ]

    missing = [str(p) for p in required if not p.exists()]
    if missing:
        print(json.dumps({"status": "fail", "missing": missing}, ensure_ascii=False))
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "db": str(paths["db"]),
                "outbox": str(paths["results"]),
                "ralph_msg": str(paths["ralph_msg"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


def run_ingest_file(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    payload = json.loads(Path(args.ingest_file).read_text(encoding="utf-8"))
    paths = ensure_dirs(root)
    init_db(paths["db"])
    resp, status = process_payload(
        root=root,
        paths=paths,
        payload=payload,
        memory_max_results=int(args.memory_max_results),
        callback_url=args.callback_url,
    )
    print(json.dumps(resp, ensure_ascii=False, indent=2))
    return 0 if status < 400 else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lobster Shell Feishu -> LongRun bridge")
    parser.add_argument("--root", default=".", help="project root")
    parser.add_argument("--host", default="127.0.0.1", help="listen host")
    parser.add_argument("--port", type=int, default=8765, help="listen port")
    parser.add_argument("--secret", default="", help="shared secret read from X-Lobster-Token header")
    parser.add_argument("--memory-max-results", type=int, default=5)
    parser.add_argument("--callback-url", default="")
    parser.add_argument("--ingest-file", default="", help="process one local payload file and exit")
    parser.add_argument("--self-check", action="store_true", help="verify local runtime prerequisites")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.self_check:
        return run_self_check(args)
    if args.ingest_file:
        return run_ingest_file(args)
    return run_server(args)


if __name__ == "__main__":
    raise SystemExit(main())
