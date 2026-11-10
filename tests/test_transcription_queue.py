import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import subprocess

import app
import transcription_queue as queue


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        app.initialize(self.data)
        app.create_project(self.data, 'chip-a', '示例')
        self.shared = self.root / 'queue'
        self.audio = self.root / 'meeting.wav'
        self.audio.write_bytes(b'RIFF sample')

    def tearDown(self):
        self.temp.cleanup()

    def test_submit_is_atomic_and_preserves_audio(self):
        job = queue.submit(self.shared, self.audio, 'chip-a')
        folder = self.shared / 'pending' / job
        self.assertEqual((folder / 'media.wav').read_bytes(), self.audio.read_bytes())
        self.assertEqual(json.loads((folder / 'job.json').read_text(encoding='utf-8'))['project'], 'chip-a')
        self.assertEqual(list((self.shared / 'staging').iterdir()), [])

    def test_invalid_files_and_projects_rejected(self):
        with self.assertRaises(ValueError): queue.submit(self.shared, self.audio, '../bad')
        p = self.root / 'bad.exe'; p.write_bytes(b'x')
        with self.assertRaises(ValueError): queue.submit(self.shared, p)

    def test_failed_job_preserves_audio_and_marks_failed(self):
        job = queue.submit(self.shared, self.audio, 'chip-a')
        result = subprocess.CompletedProcess([], 1, '', 'simulated failure')
        with patch.object(queue.subprocess, 'run', return_value=result):
            self.assertEqual(queue.process_one(self.shared, self.data, Path('python')), (job, 'failed'))
        self.assertEqual((self.shared / 'failed' / job / 'media.wav').read_bytes(), self.audio.read_bytes())
        self.assertFalse(json.loads((self.shared / 'failed' / job / 'result.json').read_text(encoding='utf-8'))['ok'])

    def test_malformed_job_is_marked_failed_without_crashing(self):
        job = queue.submit(self.shared, self.audio, 'chip-a')
        (self.shared / 'pending' / job / 'job.json').write_text('[]', encoding='utf-8')
        self.assertEqual(queue.process_one(self.shared, self.data, Path('python')), (job, 'failed'))
        self.assertTrue((self.shared / 'failed' / job / 'media.wav').exists())

    def test_completed_job_exposes_result_in_shared_queue(self):
        job = queue.submit(self.shared, self.audio, 'chip-a')
        transcript = self.data / 'transcripts' / 'example.json'
        transcript.parent.mkdir()
        transcript.write_text('{"text":"hello"}', encoding='utf-8')
        result = subprocess.CompletedProcess([], 0, json.dumps({'path': str(transcript), 'device':'cuda', 'model':'small'}), '')
        with patch.object(queue.subprocess, 'run', return_value=result):
            self.assertEqual(queue.process_one(self.shared, self.data, Path('python')), (job, 'done'))
        self.assertEqual(json.loads((self.shared / 'done' / job / 'transcript.json').read_text(encoding='utf-8'))['text'], 'hello')
        self.assertEqual(queue.process_one(self.shared, self.data, Path('python')), (None, 'empty'))


if __name__ == '__main__':
    unittest.main()
