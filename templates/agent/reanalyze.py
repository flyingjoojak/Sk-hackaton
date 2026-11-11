#!/usr/bin/env python3
"""조건이 바뀌면 단일 공급 집합의 차이만 다시 계산한다.

문장 예: "거래처 B 부도", "국가 ZZ 수출통제", "wafer 단가 상한 1000".
규칙이 읽으면 LLM 을 부르지 않는다. 규칙이 실패하고 OPENAI_API_KEY 가 있으면
OpenAI 호환 /chat/completions 를 한 번 부른다. 출력 type 이 허용 목록이 아니면 버린다.
테스트는 llm 인자를 넣어 네트워크를 타지 않는다.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

TYPES = {
    "supplier_failure": ("company_id",),
    "country_control": ("country",),
    "price_cap": ("product", "max_unit_price"),
}


def _graph():
    try:
        import graph_ref as g
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
        import graph_ref as g
    return g


def validate_condition(obj):
    if not isinstance(obj, dict):
        raise ValueError("조건은 JSON 객체여야 함")
    kind = obj.get("type")
    if kind not in TYPES:
        raise ValueError(f"허용되지 않은 type: {kind}")
    out = {"type": kind}
    for key in TYPES[kind]:
        value = obj.get(key)
        if value is None or value == "":
            raise ValueError(f"필수 키 없음: {key}")
        if key == "max_unit_price":
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError("max_unit_price 가 숫자가 아님") from None
        out[key] = value
    return out


def parse_rule(text):
    """세 가지 문장만 읽는다. 못 읽으면 ValueError. 숫자를 지어내지 않는다."""
    import re

    raw = text.strip()
    m = re.search(r"거래처\s*(\S+?)\s*부도", raw)
    if m:
        return {"type": "supplier_failure", "company_id": m.group(1).strip(".,")}
    m = re.search(r"국가\s*(\S+?)\s*수출통제", raw)
    if m:
        return {"type": "country_control", "country": m.group(1).strip(".,")}
    m = re.search(r"(\S+)\s*단가\s*상한\s*([0-9][0-9,]*(?:\.[0-9]+)?)", raw)
    if m:
        return {
            "type": "price_cap",
            "product": m.group(1),
            "max_unit_price": float(m.group(2).replace(",", "")),
        }
    raise ValueError("규칙으로 읽지 못함. 거래처 ID 부도, 국가 코드 수출통제, 자재 단가 상한 숫자 중 하나로 말해 주세요.")


def default_llm(text):
    """키가 있을 때만 호출한다. 키 값은 로그에 남기지 않는다."""
    key = os.environ.get("OPENAI_API_KEY") or ""
    model = os.environ.get("OPENAI_MODEL") or ""
    if not key or not model:
        raise ValueError("OPENAI_API_KEY 또는 OPENAI_MODEL 이 없음")
    base = (os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": (
                "거래 조건 한 개만 JSON으로 답한다. 다른 말은 하지 않는다. "
                "type은 supplier_failure(company_id), country_control(country), "
                "price_cap(product, max_unit_price) 중 하나."
            )},
            {"role": "user", "content": text},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        payload = json.loads(res.read().decode("utf-8"))
    return payload["choices"][0]["message"]["content"]


def parse_request(text, llm=None, allow_env=True):
    try:
        return validate_condition(parse_rule(text)), "rule"
    except ValueError as err:
        rule_error = str(err)
    if llm is None and allow_env and os.getenv("OPENAI_API_KEY"):
        llm = default_llm
    if llm is None:
        raise ValueError(rule_error)
    raw = llm(text).strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as err:
        raise ValueError("LLM 출력이 JSON이 아님") from err
    try:
        return validate_condition(obj), "llm"
    except ValueError as err:
        raise ValueError(f"LLM 출력 거부: {err}") from err


def _qty(row):
    try:
        return float(str(row.get("qty", "")).replace(",", ""))
    except (TypeError, ValueError):
        return None


def apply_rows(rows, companies, condition):
    """조건에 맞는 행을 뺀 새 리스트. 원본 rows 는 바꾸지 않는다."""
    cond = validate_condition(condition)
    g = _graph()
    note = {"skipped_no_qty": 0}
    if cond["type"] == "supplier_failure":
        kept = [dict(r) for r in rows if r["supplier"] != cond["company_id"]]
    elif cond["type"] == "country_control":
        ban = set(g.ids_in_country(companies, cond["country"]))
        kept = [dict(r) for r in rows if r["supplier"] not in ban]
        note["suppliers"] = sorted(ban)
    else:
        cap = cond["max_unit_price"]
        kept = []
        for row in rows:
            if row["product"] != cond["product"]:
                kept.append(dict(row))
                continue
            qty = _qty(row)
            if qty is None or qty <= 0:
                kept.append(dict(row))
                note["skipped_no_qty"] += 1
                continue
            unit = row["amount"] / qty
            if unit > cap + 1e-12:  # 단가 == 상한이면 유지
                continue
            kept.append(dict(row))
    return kept, cond, note


def reanalyze(rows, companies, condition, threshold=1.0):
    g = _graph()
    before_edges, _ = g.clean_edges(rows)
    before = g.single_source(before_edges, threshold)
    kept, cond, note = apply_rows(rows, companies, condition)
    after_edges, dropped = g.clean_edges(kept)
    after = g.single_source(after_edges, threshold)
    return {
        "condition": cond,
        "note": note,
        "diff": g.diff_single(before, after),
        "before": before,
        "after": after,
        "dropped": dropped,
    }


def explain(result):
    diff = result["diff"]
    lines = [f"조건 {result['condition']['type']}"]
    lines.append(f"단일 공급 추가 {len(diff['added'])}건, 삭제 {len(diff['removed'])}건")
    for buyer, product, supplier in diff["added"]:
        lines.append(f"추가 {buyer} / {product} / {supplier}")
    for buyer, product, supplier in diff["removed"]:
        lines.append(f"삭제 {buyer} / {product} / {supplier}")
    if result["note"].get("skipped_no_qty"):
        lines.append(f"단가를 몰라 유지한 행 {result['note']['skipped_no_qty']}건")
    if not diff["added"] and not diff["removed"]:
        lines.append("단일 공급 집합은 변하지 않았다.")
    return "\n".join(lines)


def demo():
    g = _graph()
    companies = {
        "B": {"name": "가짜소재", "country": "ZZ", "industry": "소재"},
        "C": {"name": "가짜가스", "country": "KR", "industry": "가스"},
    }
    for text in ("거래처 B 부도", "국가 ZZ 수출통제"):
        cond, via = parse_request(text, allow_env=False)
        result = reanalyze(g.SAMPLE, companies, cond)
        print(f"# {text} ({via})")
        print(explain(result))
    print("OK")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    demo()
