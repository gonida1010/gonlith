# eval/datasets.toml의 외부 평가 데이터를 고정 커밋에서 내려받아 캐시에 두고 크기·SHA-256을 잠금 파일에 기록·대조한다 (docs/research.md §9)
import argparse
import hashlib
import json
import sys
import tomllib
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY = PROJECT_ROOT / "eval" / "datasets.toml"
CHUNK_BYTES = 1 << 20


def sha256_of(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    with urllib.request.urlopen(url) as response, partial.open("wb") as handle:
        for block in iter(lambda: response.read(CHUNK_BYTES), b""):
            handle.write(block)
    partial.replace(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*", help="dataset ids to fetch (default: all)")
    args = parser.parse_args()
    registry = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
    cache = PROJECT_ROOT / registry["cache_dir"]
    lock_path = PROJECT_ROOT / registry["lock_file"]
    lock = json.loads(lock_path.read_text(encoding="utf-8")) if lock_path.exists() else {}
    failures = 0
    for dataset in registry["dataset"]:
        if args.only and dataset["id"] not in args.only:
            continue
        for path in dataset["files"]:
            key = f"{dataset['id']}@{dataset['revision']}/{path}"
            target = cache / dataset["id"] / dataset["revision"] / path
            if not target.exists():
                download(registry["base_url"].format(id=dataset["id"], revision=dataset["revision"], path=path), target)
            record = {"size": target.stat().st_size, "sha256": sha256_of(target)}
            if key in lock and lock[key] != record:
                print(f"MISMATCH {key}: locked {lock[key]} got {record}", file=sys.stderr)
                failures += 1
                continue
            lock.setdefault(key, record)
            print(f"ok {record['size']:>12,d} {key}")
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
