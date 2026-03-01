import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "feishu_longrun_daemon.py"
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


if __name__ == "__main__":
    unittest.main()
