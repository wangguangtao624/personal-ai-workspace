import hashlib
import json
import stat
from pathlib import Path
import tempfile
import unittest
import zipfile

import backup


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / 'data'
        self.data.mkdir()
        (self.data / '.personal-ai-workspace').write_text('v1', encoding='utf-8')
        (self.data / 'attachments').mkdir()
        (self.data / 'attachments' / 'audio.wav').write_bytes(b'RIFF\x00\x01test')
        (self.data / 'profile.md').write_text('中文背景', encoding='utf-8')
        (self.data / 'empty').mkdir()
        self.archive = self.root / 'snapshot.zip'

    def tearDown(self):
        self.tmp.cleanup()

    def test_real_restore_includes_audio_and_preserves_bytes(self):
        backup.create(self.data, self.archive)
        backup.verify(self.archive)
        target = self.root / 'restored'
        backup.verify(self.archive, target)
        self.assertEqual((target / 'attachments' / 'audio.wav').read_bytes(), (self.data / 'attachments' / 'audio.wav').read_bytes())
        self.assertEqual((target / 'profile.md').read_text(encoding='utf-8'), '中文背景')
        self.assertTrue((target / 'empty').is_dir())

    def test_create_or_restore_will_not_overwrite(self):
        self.archive.write_bytes(b'important')
        with self.assertRaises(ValueError): backup.create(self.data, self.archive)
        self.assertEqual(self.archive.read_bytes(), b'important')
        self.archive.unlink()
        backup.create(self.data, self.archive)
        target = self.root / 'existing'
        target.mkdir()
        (target / 'keep').write_text('safe', encoding='utf-8')
        with self.assertRaises(ValueError): backup.verify(self.archive, target)
        self.assertEqual((target / 'keep').read_text(encoding='utf-8'), 'safe')

    def test_backup_with_modified_contents_fails_and_no_restore_left(self):
        backup.create(self.data, self.archive)
        changed = self.root / 'changed.zip'
        with zipfile.ZipFile(self.archive) as original, zipfile.ZipFile(changed, 'w') as out:
            for info in original.infolist():
                content = original.read(info)
                if info.filename == 'data/profile.md': content = b'altered'
                out.writestr(info.filename, content)
        target = self.root / 'failed-restore'
        with self.assertRaises(ValueError): backup.verify(changed, target)
        self.assertFalse(target.exists())

    def test_zip_traversal_is_rejected_without_writing_outside(self):
        content = b'bad'
        manifest = {'format': 'personal-ai-backup-v1', 'directories': [], 'files': [
            {'path': '../escape.txt', 'size': len(content), 'sha256': hashlib.sha256(content).hexdigest()}]}
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('manifest.json', json.dumps(manifest))
            z.writestr('data/../escape.txt', content)
        with self.assertRaises(ValueError): backup.verify(self.archive, self.root / 'out')
        self.assertFalse((self.root / 'escape.txt').exists())
        self.assertFalse((self.root / 'out').exists())

    def test_backup_cannot_be_created_inside_source(self):
        with self.assertRaises(ValueError): backup.create(self.data, self.data / 'backup.zip')
        self.assertFalse((self.data / 'backup.zip').exists())

    def test_archive_symlink_and_windows_path_are_rejected(self):
        for bad_path in ('..\\escape', 'C:/escape', 'folder/../escape'):
            with self.subTest(path=bad_path):
                with self.assertRaises(ValueError): backup.safe_relative(bad_path)
        payload = b'target'
        manifest = {'format': 'personal-ai-backup-v1', 'directories': [], 'files': [
            {'path': 'link', 'size': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}]}
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('manifest.json', json.dumps(manifest))
            info = zipfile.ZipInfo('data/link')
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(info, payload)
        with self.assertRaises(ValueError): backup.verify(self.archive)


if __name__ == '__main__':
    unittest.main()
