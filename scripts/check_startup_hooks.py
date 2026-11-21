# site-packages의 시작 시 자동 실행 파일(.pth·sitecustomize)을 승인 해시와 대조해 승인되지 않은 훅을 찾는 표준 라이브러리 전용 검사기
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_PATH = PROJECT_ROOT / "config" / "startup_hooks.json"
DEFAULT_VENV = PROJECT_ROOT / ".venv"
STARTUP_MODULES = ("sitecustomize.py", "usercustomize.py")
PTH_IMPORT = re.compile(r"^import\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hook_files(site_packages):
    pth_files = list(site_packages.glob("*.pth"))
    files = set(pth_files)
    files.update(site_packages / name for name in STARTUP_MODULES if (site_packages / name).exists())
    for pth in pth_files:
        for module in PTH_IMPORT.findall(pth.read_text(encoding="utf-8", errors="replace")):
            target = site_packages / f"{module}.py"
            if target.exists():
                files.add(target)
    return sorted(files)


def is_project_path_pth(path):
    if path.suffix != ".pth":
        return False
    lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
    entries = [line for line in lines if line and not line.startswith("#")]
    return bool(entries) and all(
        not line.startswith("import") and Path(line).resolve().is_relative_to(PROJECT_ROOT) for line in entries
    )


def violations(venv):
    allowlist = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    found = []
    for site_packages in Path(venv).glob("lib/python*/site-packages"):
        for path in hook_files(site_packages):
            if is_project_path_pth(path):
                continue
            digest = _sha256(path)
            if allowlist.get(path.name) != digest:
                found.append(f"{path} sha256={digest}")
    return found


def main():
    venv = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_VENV
    found = violations(venv)
    for line in found:
        print(f"unapproved startup hook: {line}", file=sys.stderr)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
