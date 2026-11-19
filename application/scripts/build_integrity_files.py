"""Rebuild the data, figure and whole-repository checksum manifests after editing."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    '.git', '.venv', '__pycache__', '.pytest_cache', '.matplotlib',
    'reproduced', 'results', 'rendered',
}
INTEGRITY_FILES = {'FILE_MANIFEST.csv', 'SHA256SUMS.txt'}


def included_files(directory: Path) -> list[Path]:
    return sorted(
        (path for path in directory.rglob('*')
         if path.is_file()
         and not set(path.relative_to(ROOT).parts).intersection(EXCLUDED_DIRS)
         and path.name != '.DS_Store'),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rebuild_data_manifest() -> None:
    manifest = ROOT / 'data/DATA_FILE_MANIFEST.csv'
    old_roles = {}
    if manifest.is_file():
        with manifest.open(encoding='utf-8', newline='') as handle:
            old_roles = {row['path']: row['role'] for row in csv.DictReader(handle)}
    with manifest.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['path', 'size_bytes', 'sha256', 'role'])
        for path in included_files(ROOT / 'data'):
            if path == manifest:
                continue
            relative = path.relative_to(ROOT).as_posix()
            writer.writerow([relative, path.stat().st_size, sha256(path),
                             old_roles.get(relative, 'analysis_or_source_data')])


def rebuild_figure_manifest() -> None:
    manifest = ROOT / 'figures/SOURCE_MANIFEST.json'
    content = json.loads(manifest.read_text(encoding='utf-8'))
    content['files'] = [
        {'path': path.relative_to(ROOT / 'figures').as_posix(),
         'bytes': path.stat().st_size, 'sha256': sha256(path)}
        for path in included_files(ROOT / 'figures') if path != manifest
    ]
    manifest.write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main() -> None:
    rebuild_data_manifest()
    rebuild_figure_manifest()
    rows = [(path.relative_to(ROOT).as_posix(), path.stat().st_size, sha256(path))
            for path in included_files(ROOT)
            if path.relative_to(ROOT).as_posix() not in INTEGRITY_FILES]
    with (ROOT / 'FILE_MANIFEST.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['path', 'bytes', 'sha256'])
        writer.writerows(rows)
    with (ROOT / 'SHA256SUMS.txt').open('w', encoding='utf-8', newline='\n') as handle:
        for path, _, digest in rows:
            handle.write(f'{digest}  {path}\n')
    print(f'Rebuilt data and figure manifests; checksums cover {len(rows)} release files.')


if __name__ == '__main__':
    main()
