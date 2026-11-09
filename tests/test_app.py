import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "workspace"
        with contextlib.redirect_stdout(io.StringIO()):
            app.initialize(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_init_is_idempotent_and_does_not_overwrite_background(self):
        profile = self.root / "context/personal/profile.md"
        profile.write_text("我的背景", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            app.initialize(self.root)
        self.assertEqual(profile.read_text(encoding="utf-8"), "我的背景")

    def test_context_respects_project_and_experience_approval(self):
        with contextlib.redirect_stdout(io.StringIO()):
            app.create_project(self.root, "chip-a", "芯片 A")
            app.create_project(self.root, "chip-b", "芯片 B")
            app.propose(self.root, "断电恢复", "chip-a", "测试复盘")
        candidate = next((self.root / "experience/candidates").glob("*.json"))
        draft = app.make_context(self.root, "chip-a", "固件测试")
        self.assertNotIn("断电恢复", draft)
        with contextlib.redirect_stdout(io.StringIO()):
            app.approve(self.root, candidate.stem)
        self.assertIn("断电恢复", app.make_context(self.root, "chip-a", "固件测试"))
        self.assertNotIn("断电恢复", app.make_context(self.root, "chip-b", "固件测试"))

    def test_intake_preserves_original_and_disallows_unknown_project(self):
        audio = Path(self.temp.name) / "原始.wav"
        audio.write_bytes(b"RIFFdata")
        with contextlib.redirect_stdout(io.StringIO()):
            app.intake(self.root, "file", str(audio), None)
        entry = json.loads(next((self.root / "inbox").glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual((self.root / entry["content"]).read_bytes(), b"RIFFdata")
        with self.assertRaises(ValueError):
            app.intake(self.root, "text", "hello", "missing")

    def test_project_id_cannot_escape_workspace(self):
        for value in ("../outside", "a/b", "..", "A"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                app.create_project(self.root, value, "项目")

    def test_chinese_sentence_retrieves_related_project_document_only(self):
        with contextlib.redirect_stdout(io.StringIO()):
            app.create_project(self.root, "chip-a", "芯片 A")
            app.create_project(self.root, "chip-b", "芯片 B")
        (self.root / "projects/chip-a/sources/firmware.md").write_text(
            "固件升级后进行断电恢复检查。", encoding="utf-8")
        (self.root / "projects/chip-b/sources/firmware.md").write_text(
            "固件升级秘密资料B。", encoding="utf-8")
        report = app.make_context(self.root, "chip-a", "请帮我规划一下芯片固件测试")
        self.assertIn("固件升级后进行断电恢复检查", report)
        self.assertIn("projects/chip-a/sources/firmware.md", report)
        self.assertNotIn("秘密资料B", report)

    def test_project_file_matches_are_bounded_and_report_truncation(self):
        with contextlib.redirect_stdout(io.StringIO()):
            app.create_project(self.root, "chip-a", "芯片 A")
        sources = self.root / "projects/chip-a/sources"
        for i in range(app.MAX_MATCHED_PROJECT_FILES + 1):
            (sources / f"{i:02}.md").write_text("固件资料", encoding="utf-8")
        report = app.make_context(self.root, "chip-a", "固件测试")
        self.assertIn("匹配结果超过", report)
        self.assertNotIn("sources/20.md", report)


if __name__ == "__main__":
    unittest.main()
