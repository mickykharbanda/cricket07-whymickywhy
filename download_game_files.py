#!/usr/bin/env python3
"""
Downloads all 36 game files listed in game/manifest.json from https://cricket07.dhaiwat.com/game/
with parallel workers and resume support.
"""
import concurrent.futures
import json
import os
import urllib.parse
import urllib.request

BASE_URL = "https://cricket07.dhaiwat.com/game/"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
GAME_DIR = os.path.join(ROOT_DIR, "game")
MANIFEST_PATH = os.path.join(GAME_DIR, "manifest.json")


def download_one(item):
    rel_path = item["path"]
    expected_size = item["size"]
    local_path = os.path.join(GAME_DIR, rel_path)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    existing = os.path.getsize(local_path) if os.path.exists(local_path) else 0
    if existing == expected_size:
        print(f"[SKIP] {rel_path} ({expected_size / 1e6:.2f} MB already complete)")
        return rel_path, expected_size

    encoded_rel = "/".join(urllib.parse.quote(part) for part in rel_path.split("/"))
    url = BASE_URL + encoded_rel
    headers = {"User-Agent": "Mozilla/5.0"}
    mode = "wb"
    if 0 < existing < expected_size:
        headers["Range"] = f"bytes={existing}-"
        mode = "ab"
        print(f"[RESUME] {rel_path} from {existing / 1e6:.2f} / {expected_size / 1e6:.2f} MB")
    else:
        print(f"[START] {rel_path} ({expected_size / 1e6:.2f} MB)")

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        if mode == "ab" and resp.status != 206:
            mode = "wb"
        with open(local_path, mode) as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)

    final_size = os.path.getsize(local_path)
    if final_size != expected_size:
        raise RuntimeError(f"{rel_path}: size mismatch ({final_size} != {expected_size})")
    print(f"[DONE] {rel_path} ({final_size / 1e6:.2f} MB)")
    return rel_path, final_size


def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    files = manifest["files"]
    total_bytes = sum(x["size"] for x in files)
    print(f"Downloading {len(files)} files ({total_bytes / 1e6:.1f} MB total)...")

    # Download smaller files + EXE first, then big archives concurrently
    files_sorted = sorted(files, key=lambda x: x["size"])
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(download_one, item) for item in files_sorted]
        for fut in concurrent.futures.as_completed(futures):
            fut.result()

    print("All game files downloaded and verified!")


if __name__ == "__main__":
    main()
