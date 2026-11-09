"""Regression cases found during the GPT-6.1 acceptance review."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch

import app
import backup


class AcceptanceRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'data'
        with contextlib.redirect_stdout(io.StringIO()):
            app.initialize(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_corrupt_candidate_is_reported_without_traceback_or_promotion(self):
        entry = '20261110T000000Z-123456abcdef'
        candidate = self.root / 'experience/candidates' / (entry + '.json')
        candidate.write_text('[]', encoding='utf-8')
        with contextlib.redirect_stderr(io.StringIO()) as err:
            result = app.main(['--data', str(self.root), 'experience', 'approve', entry])
        self.assertEqual(result, 1)
        self.assertIn('错误', err.getvalue())
        self.assertTrue(candidate.exists())
        self.assertFalse((self.root / 'experience/approved' / candidate.name).exists())

    def test_candidate_cannot_promote_unknown_scope_or_changed_id(self):
        entry = '20261110T000000Z-123456abcdef'
        candidate = self.root / 'experience/candidates' / (entry + '.json')
        for change in ({'scope': 'missing'}, {'id': 'other'}, {'status': 'approved'}, {'text': ''}):
            record = {'id': entry, 'scope': 'general', 'status': 'candidate', 'text': '规则', 'source': '反馈'}
            record.update(change)
            candidate.write_text(json.dumps(record), encoding='utf-8')
            with self.subTest(change=change), self.assertRaises(ValueError):
                app.approve(self.root, entry)
            self.assertTrue(candidate.exists())

    def test_unreadable_directory_does_not_create_incomplete_backup(self):
        archive = Path(self.tmp.name) / 'backup.zip'
        def walk(*args, **kwargs):
            error = PermissionError('unreadable directory')
            if kwargs.get('onerror'):
                kwargs['onerror'](error)
            return iter(())
        with patch.object(backup.os, 'walk', side_effect=walk):
            with self.assertRaises(PermissionError):
                backup.create(self.root, archive)
        self.assertFalse(archive.exists())

    def test_invalid_utf8_manifest_is_cleanly_reported(self):
        import zipfile
        import sys
        archive = Path(self.tmp.name) / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('manifest.json', b'\xff')
        with patch.object(sys, 'argv', ['backup.py', 'verify', str(archive)]):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(backup.main(), 1)

    def test_version_prefix_does_not_displace_exact_version(self):
        with contextlib.redirect_stdout(io.StringIO()):
            app.create_project(self.root, 'chip-a', 'A')
        sources = self.root / 'projects/chip-a/sources'
        for i in range(21):
            (sources / f'{i:02}.md').write_text('固件 V1.2.30', encoding='utf-8')
        (sources / 'zz.md').write_text('固件 V1.2.3', encoding='utf-8')
        report = app.make_context(self.root, 'chip-a', '固件 V1.2.3')
        self.assertIn('sources/zz.md', report)

    def test_cli_capture_context_and_restore_end_to_end(self):
        code = Path(app.__file__).parent
        def run(script, *args):
            result = subprocess.run([sys.executable, str(code / script), *map(str, args)],
                                    capture_output=True, encoding='utf-8', timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout
        run('app.py', '--data', self.root, 'project', 'create', 'chip-a', '--name', '验收样例')
        run('app.py', '--data', self.root, 'intake', '--type', 'text', '--value', '固件需求待确认', '--project', 'chip-a')
        report = run('app.py', '--data', self.root, 'context', '--project', 'chip-a', '--task', '固件测试')
        self.assertIn('projects/chip-a/overview.md', report)
        archive = Path(self.tmp.name) / 'complete.zip'
        restored = Path(self.tmp.name) / 'restored'
        run('backup.py', 'create', '--data', self.root, '--output', archive)
        run('backup.py', 'verify', archive)
        run('backup.py', 'restore', archive, '--dest', restored)
        self.assertEqual(sorted(p.name for p in (self.root / 'inbox').iterdir()),
                         sorted(p.name for p in (restored / 'inbox').iterdir()))
        self.assertIn('验收样例', run('app.py', '--data', restored, 'context', '--project', 'chip-a', '--task', '固件测试'))


if __name__ == '__main__':
    unittest.main()
