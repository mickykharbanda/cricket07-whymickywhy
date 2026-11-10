#!/usr/bin/env python3
"""Build the public site, verified game downloads, and separate source/runtime kits."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
SOURCE_PATHS = ['README.md', 'LICENSE', 'LICENSES', '.gitignore', 'netlify.toml', 'site', 'tools', 'mod-tools', 'mods', 'engine', 'content']
FORBIDDEN_SUFFIXES = {'.exe', '.gob', '.big', '.viv', '.vp6', '.wasm', '.pyc'}
EXCLUDED_NAMES = {'.git', '.netlify', '__pycache__', '.DS_Store', 'dist', 'node_modules'}
GAME_EXE_SHA256 = 'd776dba0cc506b968f7d228e036cf42aeb4abe45a8d1ad0d7226cdebf91553a2'
PUBLIC_GAME_BASE = 'https://cricket07-whymickywhy.netlify.app/play/game/'

def stage_game_assets(directory):
    directory = directory.resolve()
    original = json.loads((directory / 'manifest.json').read_text())
    target = DIST / 'play/game'
    pieces = target / 'chunks'
    pieces.mkdir(parents=True)
    files = []
    for item in original['files']:
        source = (directory / item['path']).resolve()
        if not source.is_relative_to(directory) or not source.is_file() or source.stat().st_size != item['size']:
            raise ValueError('Missing or mismatched game file: ' + item['path'])
        chunks = []
        sha = hashlib.sha256()
        offset = 0
        with source.open('rb') as stream:
            while data := stream.read(8 * 1024 * 1024):
                chunk_hash = hashlib.sha256(data).hexdigest()
                name = chunk_hash + '.bin'
                if not (pieces / name).exists(): (pieces / name).write_bytes(data)
                chunks.append(dict(path='chunks/' + name, offset=offset, size=len(data), sha256=chunk_hash))
                sha.update(data); offset += len(data)
        files.append(dict(path=item['path'], size=item['size'], sha256=sha.hexdigest(), chunks=chunks))
    signature = json.dumps([(f['path'], f['sha256']) for f in files], separators=(',', ':')).encode()
    manifest = dict(version='hosted-' + hashlib.sha256(signature).hexdigest()[:16], files=files)
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest

def source_files():
    for name in SOURCE_PATHS:
        path = ROOT / name
        candidates = sorted(path.rglob('*')) if path.is_dir() else [path]
        for file in candidates:
            if not file.is_file():
                continue
            rel = file.relative_to(ROOT)
            if any(part in EXCLUDED_NAMES for part in rel.parts) or any(part.startswith('.env') for part in rel.parts):
                continue
            if file.suffix.lower() in FORBIDDEN_SUFFIXES or rel.parts[:3] == ('site', 'play', 'build'):
                continue
            yield file, rel

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', required=True, type=Path, help='Directory containing your compiled recomp.js and recomp.wasm (engine/build_web.sh: engine/build_web/www)')
    parser.add_argument('--game-exe', required=True, type=Path, help='The explicitly supplied original Cricket 07 executable for this release')
    parser.add_argument('--game-dir', required=True, type=Path, help='The explicitly supplied game folder and its file manifest for automatic browser downloads')
    args = parser.parse_args()
    executable = args.game_exe.resolve()
    if not executable.is_file() or hashlib.sha256(executable.read_bytes()).hexdigest() != GAME_EXE_SHA256:
        parser.error('The EXE does not match the explicitly supplied Cricket 07 build. No executable will be published.')
    runtime = args.runtime.resolve()
    for name in ['recomp.js', 'recomp.wasm']:
        if not (runtime / name).is_file():
            parser.error(f'Missing compiled runtime: {runtime / name}')
    if DIST.exists():
        for child in DIST.iterdir():
            if child.is_dir(): shutil.rmtree(child)
            else: child.unlink()
    else:
        DIST.mkdir()
    shutil.copytree(ROOT / 'site', DIST, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.DS_Store', '__pycache__', 'build'))
    build = DIST / 'play/build'
    build.mkdir(parents=True)
    for file in sorted(runtime.glob('recomp.*')):   # recomp.js, recomp.wasm (and a worker file, if the build has one)
        shutil.copy2(file, build / file.name)
    for license_file in (ROOT / 'LICENSES').glob('*.txt'):
        shutil.copy2(license_file, DIST / 'assets/fonts' / license_file.name)
    game_manifest = stage_game_assets(args.game_dir)
    for pack, blob in [('modern-2026', 'modern-pack.bin'), ('world-2026', 'world-pack.bin')]:
        target = DIST / 'play/mods' / pack
        target.mkdir(parents=True)
        manifest = json.loads((ROOT / 'mods' / pack / 'manifest.json').read_text())
        # A pack with parts ships only its parts: no file over the host's 25 MiB limit.
        names = [p['file'] for p in manifest['parts']] if manifest.get('parts') else [blob]
        for name in ['manifest.json'] + names:
            shutil.copy2(ROOT / 'mods' / pack / name, target / name)
        payload = b''.join((target / name).read_bytes() for name in names)
        assert manifest['file'] == blob
        assert len(payload) == manifest['size'] and hashlib.sha256(payload).hexdigest() == manifest['sha256']
        for resource in manifest['resources']:
            body = payload[resource['offset']:resource['offset'] + resource['size']]
            assert hashlib.sha256(body).hexdigest() == resource['sha256']
    downloads = DIST / 'downloads'
    downloads.mkdir()
    shutil.copy2(executable, downloads / 'Cricket07.exe')
    (downloads / 'Cricket07.exe.sha256').write_text(GAME_EXE_SHA256 + '  Cricket07.exe\n')
    shutil.copy2(ROOT / 'LICENSE', downloads / 'LICENSE.txt')
    prompts = json.loads((ROOT / 'site/prompts.json').read_text())
    prompt_markdown = '# Customize Cricket 07 with a coding assistant\n\nDownload the project ZIP, extract it and open that folder in Claude Code, Codex or another file-editing coding assistant. Fill in the brackets. These starter prompts describe the changes you can make; they are not a transcript of how the original port was built.\n\n'
    for key, title in [('team', 'Your own team'), ('kit', 'Your own kit'), ('site', 'Your own page')]:
        prompt_markdown += f'## {title}\n\n```text\n{prompts[key]}\n```\n\n'
    (downloads / 'CUSTOMIZE-WITH-AI.md').write_text(prompt_markdown)
    (ROOT / 'content/CUSTOMIZE-WITH-AI.md').write_text(prompt_markdown)
    with zipfile.ZipFile(downloads / 'cricket07-micky-source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for file, rel in source_files():
            archive.write(file, Path('cricket07-micky-source') / rel)
    with zipfile.ZipFile(downloads / 'cricket07-browser-build.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(DIST.rglob('*')):
            if file.is_file() and 'downloads' not in file.relative_to(DIST).parts and not file.is_relative_to(DIST / 'play/game'):
                archive.write(file, Path('cricket07-browser-build') / file.relative_to(DIST))
        portable_manifest = json.loads(json.dumps(game_manifest))
        for file in portable_manifest['files']:
            for chunk in file['chunks']: chunk['path'] = PUBLIC_GAME_BASE + chunk['path']
        archive.writestr('cricket07-browser-build/play/game/manifest.json', json.dumps(portable_manifest, indent=2))
        archive.write(ROOT / 'tools/serve.py', 'cricket07-browser-build/serve.py')
        archive.write(ROOT / 'content/LOCAL-PLAY.md', 'cricket07-browser-build/START-HERE.md')
        archive.write(ROOT / 'LICENSE', 'cricket07-browser-build/LICENSE')
        archive.write(executable, 'cricket07-browser-build/game-executable/Cricket07.exe')
    with zipfile.ZipFile(downloads / 'cricket07-micky-source.zip') as archive:
        assert archive.testzip() is None
        assert not any(Path(name).suffix.lower() in FORBIDDEN_SUFFIXES for name in archive.namelist())
    for file in DIST.rglob('*'):
        if file.is_file():
            assert not any(part.startswith('.env') or part in EXCLUDED_NAMES for part in file.relative_to(DIST).parts)
            if file.suffix.lower() == '.exe':
                assert file == downloads / 'Cricket07.exe' and hashlib.sha256(file.read_bytes()).hexdigest() == GAME_EXE_SHA256
            assert file.suffix.lower() not in {'.gob', '.big', '.viv', '.vp6'}
    print(f'Built {len(list(DIST.rglob("*")))} paths; verified {len(manifest["resources"])} mod resources and the requested EXE. Hosted {len(game_manifest["files"])} game files ({sum(f["size"] for f in game_manifest["files"])/1e6:.0f} MB) as verified chunks.')
    for file in downloads.iterdir():
        print(f'{file.name}: {file.stat().st_size / 1e6:.1f} MB')

if __name__ == '__main__':
    main()
