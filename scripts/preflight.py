#!/usr/bin/env python3
"""환경 점검과 제출 전 점검. 표준 라이브러리만.

사용:
  python3 scripts/preflight.py          # 시작 직후: 환경만
  python3 scripts/preflight.py submit   # 제출 전: 환경 + 테스트 + 남은 것
종료 코드: 0 문제 없음 / 1 문제 있음 / 2 확인한 것이 없음(통과로 읽지 말 것)
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys

ROOT = os.getcwd()
SKIP_DIRS = {".git", ".agents", "node_modules", "__pycache__", ".venv", "venv"}
SECRET = re.compile(
    r"(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY)"
)
results = []


def add(status, name, detail=""):
    results.append(status)
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""))


def _captured(proc):
    return proc.returncode, proc.stdout + proc.stderr


def run_pytest(ignore_templates):
    # shell 을 쓰지 않는다. 인자는 여기 적힌 목록만이다.
    try:
        if ignore_templates:
            proc = subprocess.run(
                ["python3", "-m", "pytest", "-q", "-rN", "--ignore=templates"],
                cwd=ROOT, capture_output=True, text=True, timeout=300, shell=False,
            )
        else:
            proc = subprocess.run(
                ["python3", "-m", "pytest", "-q", "-rN"],
                cwd=ROOT, capture_output=True, text=True, timeout=300, shell=False,
            )
        return _captured(proc)
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def run_unittest(in_tests_dir):
    try:
        if in_tests_dir:
            proc = subprocess.run(
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"],
                cwd=ROOT, capture_output=True, text=True, timeout=300, shell=False,
            )
        else:
            proc = subprocess.run(
                ["python3", "-m", "unittest", "discover", "-s", ".", "-v"],
                cwd=ROOT, capture_output=True, text=True, timeout=300, shell=False,
            )
        return _captured(proc)
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def run_git_status():
    try:
        proc = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT, capture_output=True, text=True, timeout=30, shell=False,
        )
        return _captured(proc)
    except (OSError, subprocess.TimeoutExpired) as e:
        return -1, str(e)


def project_files(exts):
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(exts):
                yield os.path.join(root, f)


def check_env():
    v = sys.version_info
    add("PASS", "python", sys.version.split()[0] + (" (3.10 미만: match, X | Y 타입 표기 금지)" if v < (3, 10) else ""))
    if v < (3, 11):
        add("PASS", "datetime", "fromisoformat 이 'Z' 를 못 읽음: s.replace('Z', '+00:00') 로 처리")
    have = [m for m in ("pandas", "numpy", "pytest", "openpyxl", "requests") if importlib.util.find_spec(m)]
    add("PASS", "외부 패키지", ", ".join(have) if have else "없음 - 표준 라이브러리로 풀 것")
    add("PASS", "도구", ", ".join(t for t in ("git", "rg", "node", "codex") if shutil.which(t)) or "없음")


def count(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else 0


def check_tests():
    # 이 저장소를 점검할 때는 templates/app 뼈대 테스트를 돌리지 않는다.
    # 뼈대는 과제 폴더로 복사한 뒤 그 폴더에서 실행한다.
    harness = os.path.isdir(os.path.join(ROOT, "templates", "app")) and os.path.isdir(os.path.join(ROOT, "tests"))
    if importlib.util.find_spec("pytest"):
        # pytest 는 unittest 형식 테스트도 함께 실행한다
        code, out = run_pytest(harness)
        skipped = count(r"(\d+) skipped", out)
        ran = count(r"(\d+) passed", out) + count(r"(\d+) failed", out) + count(r"(\d+) error", out) + skipped
    else:
        code, out = run_unittest(harness)
        ran = count(r"Ran (\d+) test", out)
        skipped = count(r"skipped=(\d+)", out)
    if ran == 0:
        add("FAIL", "테스트", "실행된 테스트 0개 (test_*.py 가 없거나 발견 안 됨)")
    elif ran == skipped:
        add("FAIL", "테스트", f"{ran}개 전부 skip")
    elif code != 0:
        add("FAIL", "테스트", out.strip().splitlines()[-1])
    else:
        add("PASS", "테스트", f"{ran}개 실행, skip {skipped}")


def check_leftovers():
    hits, scanned = [], 0
    for path in project_files((".py", ".md", ".txt", ".json", ".csv", ".yaml", ".yml", ".toml", ".env")):
        scanned += 1
        with open(path, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        rel = os.path.relpath(path, ROOT)
        if SECRET.search(text):
            hits.append(f"비밀값 의심: {rel}")
        marker = "TO" + "DO"
        if rel == "README.md" and re.search(r"\b" + marker + r"\b|미구현|" + "TB" + "D", text):
            hits.append("README 에 미구현 표시가 남음")
        if rel.endswith(".py") and re.search(r"\b" + marker + r"\b|breakpoint\s*\(|pdb\.set_trace\s*\(", text):
            hits.append(f"남은 코드: {rel}")
    if scanned == 0:
        add("NOT_RUN", "남은 것 검사", "검사한 파일 0개")
    elif hits:
        add("FAIL", "남은 것 검사", "; ".join(hits))
    else:
        add("PASS", "남은 것 검사", f"파일 {scanned}개")
    code, out = run_git_status()
    if code != 0:
        tail = out.strip().splitlines()[-1] if out.strip() else str(code)
        add("FAIL", "git", f"status 실패: {tail}")
    else:
        dirty = [l for l in out.splitlines() if not re.search(r"__pycache__|.pytest_cache|.pyc$", l)]
        add("FAIL" if dirty else "PASS", "git", f"미커밋 {len(dirty)}개" if dirty else "깨끗함")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    check_env()
    if sys.argv[1:] == ["submit"]:
        check_tests()
        check_leftovers()
    if "FAIL" in results:
        return 1
    if results.count("PASS") == 0:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
