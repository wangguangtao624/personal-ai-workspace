#!/usr/bin/env python3
"""Transcribe a local audio/video file using the user's douyin-insight engine."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from datetime import datetime, timezone
from uuid import uuid4


def main():
    parser = argparse.ArgumentParser(description='使用本机已有的 faster-whisper 转写音视频')
    parser.add_argument('media', help='本机音频或视频文件')
    parser.add_argument('--data', default='data', help='已初始化的知识库数据目录')
    parser.add_argument('--project', help='可选，已创建的项目 ID')
    parser.add_argument('--skill-dir', default=os.environ.get('DOUYIN_INSIGHT_DIR', str(Path.home() / '.codex/skills/douyin-insight')))
    parser.add_argument('--model', default='small')
    parser.add_argument('--device', choices=('cuda', 'cpu', 'auto'), default='cuda')
    parser.add_argument('--language', default='auto')
    parser.add_argument('--source-name', help='来源显示名称，不作为文件路径')
    args = parser.parse_args()
    try:
        import app
        root = Path(args.data).expanduser().resolve()
        app.ensure_initialized(root)
        if args.project:
            app.get_project(root, args.project)
        media = Path(args.media).expanduser().resolve(strict=True)
        if not media.is_file():
            raise ValueError('音视频文件不存在。')
        script_dir = Path(args.skill_dir).expanduser().resolve() / 'scripts'
        if not (script_dir / 'core' / 'transcribe.py').is_file():
            raise ValueError('找不到抖音洞察技能的转写模块。')
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(script_dir))
        from core import transcribe
        engine = transcribe.Engine()
        # Prevent implicit model downloads; users can explicitly provision models separately.
        if not engine._snapshot(args.model):
            raise ValueError('本机没有指定模型，请先配置已有模型缓存。')
        result = engine.transcribe(media, size=args.model, device=args.device,
                                   language=args.language, timestamps=True, workers=1)
        ident = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:12]
        directory = root / 'transcripts'
        if directory.is_symlink() or getattr(directory, 'is_junction', lambda: False)():
            raise ValueError('转写目录不能是链接。')
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / (ident + '.json')
        payload = {'id': ident, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                   'project': args.project, 'source_name': args.source_name or media.name, 'result': result,
                   'note': '机器转写，人物、数字和术语需核对原音视频。'}
        app.write_atomic(output, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
        source_path = None
        if args.project:
            # Store an explicitly unverified text copy under this project for retrieval.
            project = app.get_project(root, args.project)
            source_dir = project / 'sources'
            if source_dir.is_symlink() or not app.is_within(source_dir, project):
                raise ValueError('项目来源目录不在项目内部。')
            source_path = source_dir / ('transcript-' + ident + '.md')
            source_label = str(payload['source_name']).replace('\n', ' ').replace('\r', ' ')
            body = ('# 音视频机器转写（待核对）\n\n' + '- 来源文件：' + source_label
                    + '\n- 逐字稿记录：' + output.relative_to(root).as_posix()
                    + '\n- 状态：机器转写，未核对\n\n' + result['text'] + '\n')
            app.write_atomic(source_path, body)
        print(json.dumps({'ok': True, 'id': ident, 'path': str(output),
                          'device': result['device'], 'model': result['model'],
                          'duration': result['duration'], 'project_source': str(source_path) if source_path else None}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    raise SystemExit(main())
