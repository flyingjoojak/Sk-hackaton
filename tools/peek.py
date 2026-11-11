#!/usr/bin/env python3
"""데이터 파일 구조를 토큰 적게 훑는다. 표준 라이브러리만.

사용: python3 tools/peek.py <파일 또는 폴더> [...]
CSV/TSV: 행 수, 열마다 빈 값 비율, 숫자 비율, 최소/최대, 상위 값 3개
JSON/JSONL: 최상위 구조와 키
그 외: 앞 5줄
"""
import csv
import json
import os
import sys
from collections import Counter

MAX_ROWS = 200_000


def to_num(v):
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def peek_csv(path, delim):
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f, delimiter=delim)
        try:
            head = next(reader)
        except StopIteration:
            print("  (빈 파일)")
            return
        body = []
        extra = False
        for row in reader:
            if len(body) >= MAX_ROWS:
                extra = True
                break
            body.append(row)
    print(f"  행 {len(body)}{' 이상' if extra else ''}, 열 {len(head)}")
    bad = sum(1 for r in body if len(r) != len(head))
    if bad:
        print(f"  주의: 열 개수가 헤더와 다른 행 {bad}개")
    for i, name in enumerate(head):
        vals = [r[i].strip() for r in body if i < len(r)]
        filled = [v for v in vals if v]
        nums = [n for n in map(to_num, filled) if n is not None]
        blank_pct = 100 * (len(vals) - len(filled)) / max(len(vals), 1)
        line = f"  - {name}: 빈값 {blank_pct:.0f}%"
        if filled and len(nums) / len(filled) > 0.9:
            line += f", 숫자 min {min(nums):g} max {max(nums):g}"
        else:
            top = Counter(filled).most_common(3)
            line += f", 고유 {len(set(filled))}, 상위 {[k for k, _ in top]}"
        print(line)


def shape(x, depth=0):
    if depth > 2:
        return "..."
    if isinstance(x, dict):
        return {k: shape(v, depth + 1) for k, v in list(x.items())[:15]}
    if isinstance(x, list):
        return [f"len={len(x)}", shape(x[0], depth + 1)] if x else []
    return type(x).__name__


def peek_json(path):
    size = os.path.getsize(path)
    if size > 2_000_000:
        print(f"  파일이 큼 ({size:,} bytes). 앞 500자만 봅니다.")
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            print("  ", f.read(500).replace("\n", " "))
        return
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        if path.endswith(".jsonl"):
            lines = []
            extra = False
            for line in f:
                if not line.strip():
                    continue
                if len(lines) >= 20:
                    extra = True
                    break
                lines.append(line)
            print(f"  줄 {len(lines)}{' 이상' if extra else ''}")
            if lines:
                print("  ", json.dumps(shape(json.loads(lines[0])), ensure_ascii=False))
            return
        print("  ", json.dumps(shape(json.load(f)), ensure_ascii=False)[:1500])


def peek(path):
    print(f"# {path} ({os.path.getsize(path):,} bytes)")
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in (".csv", ".tsv"):
            peek_csv(path, "\t" if ext == ".tsv" else ",")
        elif ext in (".json", ".jsonl"):
            peek_json(path)
        else:
            with open(path, encoding="utf-8", errors="replace") as f:
                for _ in range(5):
                    line = f.readline()
                    if not line:
                        break
                    print("  " + line.rstrip()[:200])
    except Exception as e:  # 한 파일 실패가 전체를 막지 않게, 이유는 출력한다
        print(f"  읽기 실패: {type(e).__name__}: {e}")


def main(args):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not args:
        print(__doc__)
        return 2
    for a in args:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                if ".git" in root:
                    continue
                for name in sorted(files):
                    peek(os.path.join(root, name))
        else:
            peek(a)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
