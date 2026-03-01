import argparse
import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "feishu_longrun_daemon.py"
REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("feishu_longrun_daemon", MODULE_PATH)
daemon = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(daemon)


class LobsterConfigTest(unittest.TestCase):
    def test_config_values_fill_cli_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / ".bagakit" / "lobster-shell"
            config_dir.mkdir(parents=True)
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "listen_host": "0.0.0.0",
                        "listen_port": 9876,
                        "shared_secret": "configured-value",
                        "memory_max_results": 9,
                        "feishu_reply_webhook": "http://127.0.0.1/callback",
                    }
                ),
                encoding="utf-8",
            )

            args = daemon.apply_lobster_config(
                argparse.Namespace(
                    root=str(root),
                    host=None,
                    port=None,
                    secret=None,
                    memory_max_results=None,
                    callback_url=None,
                )
            )

            self.assertEqual(args.host, "0.0.0.0")
            self.assertEqual(args.port, 9876)
            self.assertEqual(args.secret, "configured-value")
            self.assertEqual(args.memory_max_results, 9)
            self.assertEqual(args.callback_url, "http://127.0.0.1/callback")

    def test_cli_values_override_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_dir = root / ".bagakit" / "lobster-shell"
            config_dir.mkdir(parents=True)
            (config_dir / "config.json").write_text(
                json.dumps(
                    {
                        "listen_host": "0.0.0.0",
                        "listen_port": 9876,
                        "shared_secret": "configured-value",
                        "memory_max_results": 9,
                        "feishu_reply_webhook": "http://127.0.0.1/callback",
                    }
                ),
                encoding="utf-8",
            )

            args = daemon.apply_lobster_config(
                argparse.Namespace(
                    root=str(root),
                    host="127.0.0.1",
                    port=8765,
                    secret="cli-value",
                    memory_max_results=3,
                    callback_url="http://127.0.0.1/cli",
                )
            )

            self.assertEqual(args.host, "127.0.0.1")
            self.assertEqual(args.port, 8765)
            self.assertEqual(args.secret, "cli-value")
            self.assertEqual(args.memory_max_results, 3)
            self.assertEqual(args.callback_url, "http://127.0.0.1/cli")


class LobsterMakefileWrapperTest(unittest.TestCase):
    def test_daemon_wrapper_preserves_config_defaults(self) -> None:
        makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("LOBSTER_SHELL_DAEMON_FLAGS", makefile)
        self.assertIn("LOBSTER_SHELL_HOST", makefile)
        self.assertIn("LOBSTER_SHELL_PORT", makefile)
        self.assertIn("--host $(LOBSTER_SHELL_HOST)", makefile)
        self.assertIn("--port $(LOBSTER_SHELL_PORT)", makefile)
        self.assertNotIn("--host 127.0.0.1", makefile)
        self.assertNotIn("--port 8765", makefile)


class LobsterProcessPayloadTest(unittest.TestCase):
    def test_post_callback_reports_exception_type_only(self) -> None:
        original_urlopen = daemon.urllib.request.urlopen

        def failing_urlopen(_request, timeout):
            raise urllib.error.URLError("callback URL refused by transport")

        daemon.urllib.request.urlopen = failing_urlopen

        try:
            status = daemon.post_callback("http://127.0.0.1/callback", {"ok": True})
        finally:
            daemon.urllib.request.urlopen = original_urlopen

        self.assertEqual(status, "error:URLError")
        self.assertNotIn("callback", status)
        self.assertNotIn("transport", status)

    def test_outbox_records_callback_status(self) -> None:
        original_recall_memory = daemon.recall_memory
        original_run_once = daemon.run_once
        original_post_callback = daemon.post_callback

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = daemon.ensure_dirs(root)
            daemon.init_db(paths["db"])
            (root / "docs" / ".bagakit" / "inbox").mkdir(parents=True)

            daemon.recall_memory = lambda *_args, **_kwargs: "(no relevant memory found)"
            daemon.run_once = lambda _paths, _root, run_id: {
                "status": "completed",
                "exit_code": 0,
                "run_id": run_id,
                "run_log": str(root / ".bagakit" / "lobster-shell" / "runtime" / "run.log"),
            }
            callback_payloads = []

            def capture_callback(_url, callback_payload):
                callback_payloads.append(dict(callback_payload))
                return "ok:200"

            daemon.post_callback = capture_callback

            try:
                response, status = daemon.process_payload(
                    root=root,
                    paths=paths,
                    payload={"message_id": "msg-callback", "text": "ship it"},
                    memory_max_results=1,
                    callback_url="http://127.0.0.1/callback",
                )
            finally:
                daemon.recall_memory = original_recall_memory
                daemon.run_once = original_run_once
                daemon.post_callback = original_post_callback

            self.assertEqual(status, 200)
            self.assertEqual(response["callback_status"], "ok:200")
            self.assertEqual(response["run_log"], ".bagakit/lobster-shell/runtime/run.log")
            self.assertFalse(Path(response["run_log"]).is_absolute())
            self.assertEqual(
                response["memory_note"],
                f"docs/.bagakit/inbox/howto-lobster-shell-{response['run_id']}.md",
            )
            self.assertFalse(Path(response["memory_note"]).is_absolute())
            self.assertEqual(len(callback_payloads), 1)
            self.assertEqual(callback_payloads[0]["run_log"], response["run_log"])
            self.assertEqual(callback_payloads[0]["memory_note"], response["memory_note"])

            outbox_lines = paths["results"].read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(outbox_lines), 1)
            outbox_payload = json.loads(outbox_lines[0])
            self.assertEqual(outbox_payload["callback_status"], "ok:200")
            self.assertEqual(outbox_payload["run_log"], response["run_log"])
            self.assertEqual(outbox_payload["memory_note"], response["memory_note"])

    def test_callback_exception_still_writes_outbox(self) -> None:
        original_recall_memory = daemon.recall_memory
        original_run_once = daemon.run_once
        original_post_callback = daemon.post_callback

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = daemon.ensure_dirs(root)
            daemon.init_db(paths["db"])
            (root / "docs" / ".bagakit" / "inbox").mkdir(parents=True)

            daemon.recall_memory = lambda *_args, **_kwargs: "(no relevant memory found)"
            daemon.run_once = lambda _paths, _root, run_id: {
                "status": "completed",
                "exit_code": 0,
                "run_id": run_id,
                "run_log": str(root / ".bagakit" / "lobster-shell" / "runtime" / "run.log"),
            }

            def failing_callback(_url, _payload):
                raise RuntimeError("callback transport exploded")

            daemon.post_callback = failing_callback

            try:
                response, status = daemon.process_payload(
                    root=root,
                    paths=paths,
                    payload={"message_id": "msg-callback-error", "text": "ship it"},
                    memory_max_results=1,
                    callback_url="http://127.0.0.1/callback",
                )
            finally:
                daemon.recall_memory = original_recall_memory
                daemon.run_once = original_run_once
                daemon.post_callback = original_post_callback

            self.assertEqual(status, 200)
            self.assertEqual(response["callback_status"], "error:RuntimeError")
            self.assertEqual(response["run_log"], ".bagakit/lobster-shell/runtime/run.log")
            self.assertFalse(Path(response["run_log"]).is_absolute())
            self.assertEqual(
                response["memory_note"],
                f"docs/.bagakit/inbox/howto-lobster-shell-{response['run_id']}.md",
            )
            self.assertFalse(Path(response["memory_note"]).is_absolute())

            outbox_lines = paths["results"].read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(outbox_lines), 1)
            outbox_payload = json.loads(outbox_lines[0])
            self.assertEqual(outbox_payload["callback_status"], "error:RuntimeError")
            self.assertEqual(outbox_payload["run_log"], response["run_log"])
            self.assertFalse(Path(outbox_payload["run_log"]).is_absolute())
            self.assertEqual(outbox_payload["memory_note"], response["memory_note"])
            self.assertFalse(Path(outbox_payload["memory_note"]).is_absolute())


if __name__ == "__main__":
    unittest.main()
