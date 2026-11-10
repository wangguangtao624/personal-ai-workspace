#!/usr/bin/env python3
"""File queue for a trusted shared folder; transport and access are external."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from uuid import uuid4

import app

EXTENSIONS = {'.wav', '.mp3', '.m4a', '.mp4', '.mov', '.mkv', '.webm', '.flac', '.aac'}
MAX_BYTES = 500 * 1024 * 1024


def setup(queue):
    queue.mkdir(parents=True, exist_ok=True)
    for name in ('staging', 'pending', 'processing', 'done', 'failed'):
        p = queue / name
        if p.is_symlink() or getattr(p, 'is_junction', lambda: False)():
            raise ValueError('队列目录不能为链接。')
        p.mkdir(exist_ok=True)


def submit(queue, source, project=None):
    setup(queue)
    source = source.expanduser().resolve(strict=True)
    suffix = source.suffix.lower()
    if not source.is_file() or suffix not in EXTENSIONS or source.stat().st_size > MAX_BYTES:
        raise ValueError('文件类型不支持或超过 500 MB。')
    if project:
        app.valid_id(project)
    job = uuid4().hex
    temp = queue / 'staging' / job
    temp.mkdir()
    try:
        shutil.copyfile(source, temp / ('media' + suffix))
        metadata = {'id': job, 'media': 'media' + suffix, 'source_name': source.name, 'project': project}
        (temp / 'job.json').write_text(json.dumps(metadata, ensure_ascii=False), encoding='utf-8')
        os.rename(temp, queue / 'pending' / job)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return job


def process_one(queue, data, python, skill_dir=None, device='cuda'):
    setup(queue)
    app.ensure_initialized(data)
    for candidate in sorted((queue / 'pending').iterdir()):
        if not re.fullmatch(r'[0-9a-f]{32}', candidate.name) or candidate.is_symlink() or not candidate.is_dir():
            continue
        current = queue / 'processing' / candidate.name
        try:
            os.rename(candidate, current)
        except (FileNotFoundError, FileExistsError):
            continue
        try:
            meta = json.loads((current / 'job.json').read_text(encoding='utf-8'))
            if not isinstance(meta, dict):
                raise ValueError('任务元数据格式错误。')
            media_name = meta['media']
            if (meta.get('id') != current.name or not isinstance(media_name, str)
                    or not re.fullmatch(r'media\.[a-z0-9]+', media_name)
                    or Path(media_name).suffix not in EXTENSIONS):
                raise ValueError('任务内容不符合约定。')
            media = current / media_name
            if media.is_symlink() or not media.is_file() or media.stat().st_size > MAX_BYTES:
                raise ValueError('媒体文件不可用。')
            command = [str(python), '-B', str(Path(__file__).with_name('transcribe_local.py')),
                       str(media), '--data', str(data), '--device', device]
            if isinstance(meta.get('source_name'), str):
                command += ['--source-name', Path(meta['source_name']).name[:255]]
            if meta.get('project'):
                command += ['--project', app.valid_id(meta['project'])]
            if skill_dir:
                command += ['--skill-dir', str(skill_dir)]
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=7200)
            if result.returncode:
                raise RuntimeError(result.stderr[-2000:] or '转写失败。')
            info = json.loads(result.stdout)
            transcript = Path(info['path'])
            if not app.is_within(transcript, data / 'transcripts'):
                raise ValueError('转写结果路径无效。')
            shutil.copyfile(transcript, current / 'transcript.json')
            (current / 'result.json').write_text(json.dumps({'ok': True, 'id': current.name,
                'device': info['device'], 'model': info['model']}, ensure_ascii=False), encoding='utf-8')
            os.rename(current, queue / 'done' / current.name)
            return current.name, 'done'
        except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
            (current / 'result.json').write_text(json.dumps({'ok': False, 'id': current.name,
                'error': str(exc)[:1000]}, ensure_ascii=False), encoding='utf-8')
            os.rename(current, queue / 'failed' / current.name)
            return current.name, 'failed'
    return None, 'empty'


def main():
    parser = argparse.ArgumentParser(description='转写队列：使用已配置的受控共享目录')
    parser.add_argument('--queue', required=True)
    actions = parser.add_subparsers(dest='action', required=True)
    add = actions.add_parser('submit')
    add.add_argument('file'); add.add_argument('--project')
    work = actions.add_parser('work-once')
    work.add_argument('--data', required=True); work.add_argument('--python', required=True)
    work.add_argument('--skill-dir'); work.add_argument('--device', choices=('cuda', 'cpu', 'auto'), default='cuda')
    args = parser.parse_args()
    try:
        queue = Path(args.queue).expanduser().resolve()
        if args.action == 'submit':
            print(json.dumps({'id': submit(queue, Path(args.file), args.project), 'state': 'pending'}))
        else:
            job, state = process_one(queue, Path(args.data).expanduser().resolve(), Path(args.python), args.skill_dir, args.device)
            print(json.dumps({'id': job, 'state': state}))
            if state == 'failed': return 1
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
