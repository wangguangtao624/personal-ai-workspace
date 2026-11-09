#!/usr/bin/env python3
"""Create and restore a local, unencrypted, integrity-checked data snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import zipfile

MANIFEST = 'manifest.json'
PREFIX = 'data/'
CHUNK = 1024 * 1024
MAX_MANIFEST = 8 * 1024 * 1024
MAX_TOTAL = 20 * 1024 * 1024 * 1024


def walk_error(error: OSError) -> None:
    raise error


def safe_relative(value: str) -> str:
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or '\x00' in value:
        raise ValueError('备份包含不安全的路径。')
    parts = value.split('/')
    if any(p in ('', '.', '..') for p in parts) or value.startswith('/'):
        raise ValueError('备份包含不安全的路径。')
    # Refuse ambiguous Windows names even when restoring on other platforms.
    for p in parts:
        stem = p.split('.')[0].upper()
        if p.endswith(('.', ' ')) or stem in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
            raise ValueError('备份包含不安全的路径。')
    return PurePosixPath(value).as_posix()


def digest_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(CHUNK), b''):
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), size


def create(source: Path, archive: Path) -> None:
    source = source.expanduser().resolve()
    archive = archive.expanduser().resolve()
    if not source.is_dir() or not (source / '.personal-ai-workspace').is_file():
        raise ValueError('请选择已初始化的数据目录。')
    if archive == source or source in archive.parents:
        raise ValueError('备份文件不能放在被备份的数据目录内。')
    if archive.exists():
        raise ValueError('备份文件已存在，请选择新文件名。')
    files, directories = [], []
    for root, dirs, names in os.walk(source, followlinks=False, onerror=walk_error):
        root_path = Path(root)
        dirs.sort(); names.sort()
        for name in dirs:
            p = root_path / name
            if p.is_symlink() or getattr(p, 'is_junction', lambda: False)():
                raise ValueError(f'不支持符号链接：{p}')
            if name == '.git':
                continue
            directories.append(safe_relative(p.relative_to(source).as_posix()))
        dirs[:] = [d for d in dirs if d != '.git']
        for name in names:
            p = root_path / name
            if p.is_symlink() or not stat.S_ISREG(p.stat().st_mode):
                raise ValueError(f'不支持符号链接或特殊文件：{p}')
            rel = safe_relative(p.relative_to(source).as_posix())
            sha, size = digest_file(p)
            files.append({'path': rel, 'sha256': sha, 'size': size})
    if sum(f['size'] for f in files) > MAX_TOTAL:
        raise ValueError('数据超过单次备份上限 20 GiB。')
    manifest = {'format': 'personal-ai-backup-v1', 'files': files, 'directories': directories}
    encoded = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
    if len(encoded) > MAX_MANIFEST:
        raise ValueError('备份清单过大。')
    created = False
    try:
        with archive.open('xb') as archive_stream:
            created = True
            with zipfile.ZipFile(archive_stream, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as z:
                z.writestr(MANIFEST, encoded)
                for entry in files:
                    path = source / Path(entry['path'])
                    # Detect source changes between scan and copy, including same-size edits.
                    h = hashlib.sha256(); size = 0
                    with path.open('rb') as src, z.open(PREFIX + entry['path'], 'w', force_zip64=True) as dst:
                        for chunk in iter(lambda: src.read(CHUNK), b''):
                            h.update(chunk); size += len(chunk); dst.write(chunk)
                    if h.hexdigest() != entry['sha256'] or size != entry['size']:
                        raise ValueError(f'备份期间文件发生变化：{entry["path"]}')
    except BaseException:
        if created: archive.unlink(missing_ok=True)
        raise


def inspect(z: zipfile.ZipFile) -> tuple[dict, dict[str, zipfile.ZipInfo]]:
    infos = z.infolist()
    names = [i.filename for i in infos]
    if len(names) != len(set(names)) or names.count(MANIFEST) != 1:
        raise ValueError('备份成员重复或缺少清单。')
    manifest_info = z.getinfo(MANIFEST)
    if manifest_info.file_size > MAX_MANIFEST:
        raise ValueError('备份清单过大。')
    manifest = json.loads(z.read(manifest_info))
    if not isinstance(manifest, dict) or manifest.get('format') != 'personal-ai-backup-v1':
        raise ValueError('不支持的备份格式。')
    files, dirs = manifest.get('files'), manifest.get('directories')
    if not isinstance(files, list) or not isinstance(dirs, list):
        raise ValueError('备份清单无效。')
    entries: dict[str, zipfile.ZipInfo] = {}
    seen: set[str] = set()
    total = 0
    for path in dirs:
        rel = safe_relative(path); key = rel.casefold()
        if key in seen: raise ValueError('备份路径重复。')
        seen.add(key)
    for item in files:
        if not isinstance(item, dict): raise ValueError('备份清单无效。')
        rel = safe_relative(item.get('path')); key = rel.casefold()
        if key in seen: raise ValueError('备份路径重复。')
        seen.add(key)
        sha, size = item.get('sha256'), item.get('size')
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha) or type(size) is not int or size < 0:
            raise ValueError('备份校验信息无效。')
        name = PREFIX + rel
        if name not in names: raise ValueError('备份文件缺失。')
        info = z.getinfo(name)
        if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16) or info.file_size != size:
            raise ValueError('备份文件类型或大小无效。')
        total += size
        entries[rel] = info
    if total > MAX_TOTAL or set(names) != {MANIFEST, *(PREFIX + p for p in entries)}:
        raise ValueError('备份包含未列明成员或超过上限。')
    return manifest, entries


def verify(archive: Path, destination: Path | None = None) -> None:
    archive = archive.expanduser().resolve()
    if destination is not None:
        destination = destination.expanduser().resolve()
        if destination.exists(): raise ValueError('恢复目标已存在，请选择不存在的新目录。')
        if not destination.parent.is_dir(): raise ValueError('恢复目标的父目录不存在。')
    created = False
    try:
        with zipfile.ZipFile(archive, 'r') as z:
            manifest, entries = inspect(z)
            if destination is not None:
                destination.mkdir(exist_ok=False); created = True
                for directory in sorted(manifest['directories'], key=lambda v: (v.count('/'), v)):
                    (destination / directory).mkdir(parents=True, exist_ok=True)
            for item in manifest['files']:
                rel = item['path']; h = hashlib.sha256(); size = 0
                target = destination / rel if destination is not None else None
                if target is not None: target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(entries[rel]) as src:
                    out = target.open('xb') if target is not None else None
                    try:
                        for chunk in iter(lambda: src.read(CHUNK), b''):
                            h.update(chunk); size += len(chunk)
                            if size > item['size']: raise ValueError('备份文件大小异常。')
                            if out: out.write(chunk)
                    finally:
                        if out: out.close()
                if size != item['size'] or h.hexdigest() != item['sha256']:
                    raise ValueError(f'备份校验失败：{rel}')
    except BaseException:
        if created and destination is not None: shutil.rmtree(destination)
        raise


def main() -> int:
    p = argparse.ArgumentParser(description='本地未加密知识库备份；请自行加密并保存独立副本')
    sub = p.add_subparsers(dest='action', required=True)
    c = sub.add_parser('create'); c.add_argument('--data', required=True); c.add_argument('--output', required=True)
    v = sub.add_parser('verify'); v.add_argument('archive')
    r = sub.add_parser('restore'); r.add_argument('archive'); r.add_argument('--dest', required=True)
    a = p.parse_args()
    try:
        if a.action == 'create': create(Path(a.data), Path(a.output)); print('备份已创建（未加密）；请执行 verify。')
        elif a.action == 'verify': verify(Path(a.archive)); print('完整性校验通过。')
        else: verify(Path(a.archive), Path(a.dest)); print('恢复完成，文件完整性校验通过。')
        return 0
    except (ValueError, OSError, zipfile.BadZipFile, KeyError, TypeError) as e:
        print(f'错误：{e}', file=sys.stderr); return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
