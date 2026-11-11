#!/usr/bin/env python3
"""기업 간 거래 그래프 참고 구현. 표준 라이브러리만. networkx 가 있으면 차수 중심성을 한 번 더 맞춘다.

companies.csv: company_id,name,country,industry
transactions.csv: buyer_id,supplier_id,product,amount,period
방향은 supplier -> buyer. amount 는 그 기간의 구매 금액.

사용: python3 tools/graph_ref.py
과제 코드에 그대로 복사하지 말고 구조를 참고해 다시 짠다.
"""
import csv
import sys
from pathlib import Path


def load_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _amount(text, where):
    try:
        return float(str(text).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ValueError(f"금액이 숫자가 아님: {where}") from None


def load_dir(folder):
    """회사와 거래를 읽는다. 원본 파일은 그대로 둔다."""
    folder = Path(folder)
    companies = {}
    for i, row in enumerate(load_csv(folder / "companies.csv"), start=2):
        cid = (row.get("company_id") or "").strip()
        if not cid:
            raise ValueError(f"companies.csv {i}행: company_id 없음")
        companies[cid] = {
            "name": (row.get("name") or "").strip(),
            "country": (row.get("country") or "").strip(),
            "industry": (row.get("industry") or "").strip(),
        }
    tx = []
    for i, row in enumerate(load_csv(folder / "transactions.csv"), start=2):
        buyer = (row.get("buyer_id") or "").strip()
        supplier = (row.get("supplier_id") or "").strip()
        product = (row.get("product") or "").strip()
        if not buyer or not supplier or not product:
            raise ValueError(f"transactions.csv {i}행: id 또는 product 없음")
        tx.append({
            "buyer": buyer,
            "supplier": supplier,
            "product": product,
            "amount": _amount(row.get("amount"), f"transactions.csv {i}행"),
            "period": (row.get("period") or "").strip(),
            "qty": (row.get("qty") or "").strip(),
        })
    return companies, tx


def clean_edges(tx):
    """금액 0 이하와 자기 거래를 빼고, 같은 키의 금액을 합친다. 입력을 바꾸지 않는다."""
    summed = {}
    dropped = []
    for row in tx:
        item = {
            "buyer": row["buyer"],
            "supplier": row["supplier"],
            "product": row["product"],
            "amount": row["amount"],
            "period": row.get("period", ""),
        }
        if item["amount"] <= 0:
            dropped.append({"reason": "amount<=0", "row": item})
            continue
        if item["buyer"] == item["supplier"]:
            dropped.append({"reason": "self", "row": item})
            continue
        key = (item["buyer"], item["supplier"], item["product"], item["period"])
        if key in summed:
            summed[key]["amount"] += item["amount"]
        else:
            summed[key] = item
    edges = list(summed.values())
    edges.sort(key=lambda e: (e["buyer"], e["product"], e["supplier"], e["period"]))
    return edges, dropped


def build_graph(edges):
    """supplier -> buyer 인접 리스트. 간선 속성은 그대로 둔다."""
    nodes = set()
    out = {}
    for e in edges:
        nodes.add(e["supplier"])
        nodes.add(e["buyer"])
        out.setdefault(e["supplier"], []).append(
            (e["buyer"], e["product"], e["amount"], e["period"])
        )
    for s in out:
        out[s].sort()
    return {"nodes": sorted(nodes), "out": out}


def _groups(edges):
    """(buyer, product) -> {supplier: amount}. 호출하는 쪽 입력을 바꾸지 않는다."""
    grouped = {}
    for e in edges:
        parts = grouped.setdefault((e["buyer"], e["product"]), {})
        parts[e["supplier"]] = parts.get(e["supplier"], 0.0) + e["amount"]
    return grouped


def concentration(edges):
    """구매자·자재별 HHI = 비중 제곱합. 0~1. 합이 0이면 hhi 는 None."""
    rows = []
    for (buyer, product), parts in _groups(edges).items():
        total = sum(parts.values())
        if total <= 0:
            hhi = None
            top_s, top_share = "", None
        else:
            hhi = sum((a / total) ** 2 for a in parts.values())
            top_s, top_a = max(parts.items(), key=lambda kv: (-kv[1], kv[0]))
            top_share = top_a / total
        ordered = tuple(sorted(parts.items(), key=lambda kv: (-kv[1], kv[0])))
        rows.append({
            "buyer": buyer,
            "product": product,
            "total": total,
            "hhi": hhi,
            "top_supplier": top_s,
            "top_share": top_share,
            "parts": ordered,
        })
    rows.sort(key=lambda r: (r["hhi"] is None, -(r["hhi"] or 0), -r["total"], r["buyer"], r["product"]))
    return rows


def single_source(edges, threshold=1.0):
    """비중 >= threshold 인 공급처. 같으면 포함한다."""
    found = []
    for (buyer, product), parts in _groups(edges).items():
        total = sum(parts.values())
        if total <= 0:
            continue
        for supplier, amount in sorted(parts.items()):
            share = amount / total
            if share + 1e-12 >= threshold:  # 같으면 포함
                found.append({
                    "buyer": buyer,
                    "product": product,
                    "supplier": supplier,
                    "share": share,
                    "amount": amount,
                })
    found.sort(key=lambda r: (r["buyer"], r["product"], -r["share"], r["supplier"]))
    return found


def degree_centrality(edges):
    """고유 상대 수 / (n-1). 간선이 없으면 빈 dict."""
    incoming = {}
    outgoing = {}
    nodes = set()
    for e in edges:
        nodes.add(e["supplier"])
        nodes.add(e["buyer"])
        outgoing.setdefault(e["supplier"], set()).add(e["buyer"])
        incoming.setdefault(e["buyer"], set()).add(e["supplier"])
    denom = max(len(nodes) - 1, 1)
    return {
        node: {
            "in": len(incoming.get(node, ())) / denom,
            "out": len(outgoing.get(node, ())) / denom,
        }
        for node in sorted(nodes)
    }


def degree_centrality_nx(edges):
    """networkx 가 없으면 None. 있으면 같은 차수 정의를 다른 라이브러리로 계산한다."""
    try:
        import networkx as nx
    except ImportError:
        return None
    g = nx.DiGraph()
    nodes = set()
    for e in edges:
        g.add_edge(e["supplier"], e["buyer"])
        nodes.add(e["supplier"])
        nodes.add(e["buyer"])
    denom = max(len(nodes) - 1, 1)
    return {
        node: {"in": g.in_degree(node) / denom, "out": g.out_degree(node) / denom}
        for node in nodes
    }


def propagate(edges, failed, max_depth=3):
    """중단 기업(깊이 0)에서 구매자 방향으로 BFS. 깊이 == max_depth 까지 포함한다.

    lost 는 그 기업으로 들어오는 간선 중, 이미 도달한 공급자의 금액만 더한 값이다.
    간접 금액은 다시 더하지 않는다.
    """
    failed = list(dict.fromkeys(failed))
    adj = {}
    for e in edges:
        adj.setdefault(e["supplier"], {})
        slot = adj[e["supplier"]]
        slot[e["buyer"]] = slot.get(e["buyer"], 0.0) + e["amount"]
    depth = {f: 0 for f in failed}
    lost = {f: 0.0 for f in failed}
    frontier = list(failed)
    while frontier:
        found = {}
        for u in frontier:
            if depth[u] >= max_depth:
                continue
            for v, amt in adj.get(u, {}).items():
                if v in depth:
                    continue
                if v not in found:
                    found[v] = [depth[u] + 1, 0.0]
                found[v][1] += amt
        frontier = []
        for v, (d, amt) in found.items():
            depth[v] = d
            lost[v] = amt
            frontier.append(v)
    affected = [
        {"id": i, "depth": depth[i], "lost": lost[i]}
        for i in depth
        if depth[i] > 0
    ]
    affected.sort(key=lambda r: (r["depth"], r["id"]))
    return {"failed": failed, "affected": affected}


def alternatives(edges, product, exclude=()):
    """같은 자재를 공급하는 기업. exclude 와 금액 내림차순, 동률이면 id."""
    ban = set(exclude)
    totals = {}
    for e in edges:
        if e["product"] != product or e["supplier"] in ban:
            continue
        totals[e["supplier"]] = totals.get(e["supplier"], 0.0) + e["amount"]
    rows = [{"supplier": s, "amount": a} for s, a in totals.items()]
    rows.sort(key=lambda r: (-r["amount"], r["supplier"]))
    return rows


def ids_in_country(companies, country):
    """country 가 정확히 같은 기업. 빈 국적은 넣지 않는다."""
    return sorted(cid for cid, row in companies.items() if row.get("country") == country and country)


def without_suppliers(edges, supplier_ids):
    """공급자가 중단된 간선을 뺀 새 리스트. 원본은 그대로 둔다."""
    ban = set(supplier_ids)
    return [dict(e) for e in edges if e["supplier"] not in ban]


def diff_single(before, after):
    b = {(r["buyer"], r["product"], r["supplier"]) for r in before}
    a = {(r["buyer"], r["product"], r["supplier"]) for r in after}
    return {"added": sorted(a - b), "removed": sorted(b - a)}


def analyze(edges, threshold=1.0, failed=None, max_depth=3):
    report = {
        "concentration": concentration(edges),
        "single": single_source(edges, threshold),
        "centrality": degree_centrality(edges),
        "graph": build_graph(edges),
    }
    if failed:
        report["propagation"] = propagate(edges, failed, max_depth)
    return report


def _bfs_pairs(edges, failed, max_depth):
    """검사기용 BFS. propagate 와 코드를 공유하지 않는다."""
    adj = {}
    for e in edges:
        adj.setdefault(e["supplier"], {}).setdefault(e["buyer"], 0.0)
        adj[e["supplier"]][e["buyer"]] += e["amount"]
    seen = {f: 0 for f in failed}
    wave = list(seen)
    while wave:
        nxt = []
        for u in wave:
            if seen[u] >= max_depth:
                continue
            for v in adj.get(u, {}):
                if v in seen:
                    continue
                seen[v] = seen[u] + 1
                nxt.append(v)
        wave = nxt
    return {(i, d) for i, d in seen.items() if d > 0}


def validate(edges, report, threshold=1.0, failed=None, max_depth=3):
    """report 를 원본 간선으로 다시 계산해 어긋나면 이유 문자열을 돌려준다."""
    errors = []
    grouped = {}
    for e in edges:
        grouped.setdefault((e["buyer"], e["product"]), {})
        parts = grouped[(e["buyer"], e["product"])]
        parts[e["supplier"]] = parts.get(e["supplier"], 0.0) + e["amount"]

    got = {(r["buyer"], r["product"]): r["hhi"] for r in report["concentration"]}
    if set(got) != set(grouped):
        errors.append("concentration 키가 간선과 다름")
    for key, parts in grouped.items():
        total = sum(parts.values())
        expect = sum((a / total) ** 2 for a in parts.values()) if total > 0 else None
        got_h = got.get(key)
        if expect is None or got_h is None or abs(got_h - expect) > 1e-9:
            errors.append(f"hhi {key[0]}/{key[1]}")

    expect_single = set()
    for (buyer, product), parts in grouped.items():
        total = sum(parts.values())
        if total <= 0:
            continue
        for supplier, amount in parts.items():
            if amount / total + 1e-12 >= threshold:  # 같으면 포함
                expect_single.add((buyer, product, supplier))
    got_single = {(r["buyer"], r["product"], r["supplier"]) for r in report["single"]}
    if got_single != expect_single:
        errors.append("단일 공급 집합이 다름")

    if failed:
        expect_pairs = _bfs_pairs(edges, list(dict.fromkeys(failed)), max_depth)
        got_pairs = {(r["id"], r["depth"]) for r in report["propagation"]["affected"]}
        if got_pairs != expect_pairs:
            errors.append("전파 깊이 집합이 다름")
        depths = {fid: 0 for fid in dict.fromkeys(failed)}
        depths.update({i: d for i, d in expect_pairs})
        for row in report["propagation"]["affected"]:
            # 손실은 한 단계 위 공급자의 직접 금액만. propagate 의 합과 다른 루프다.
            expect_lost = sum(
                e["amount"]
                for e in edges
                if e["buyer"] == row["id"] and depths.get(e["supplier"]) == row["depth"] - 1
            )
            if abs(expect_lost - row["lost"]) > 1e-6:
                errors.append(f"손실 금액 {row['id']}")
    return errors


SAMPLE = [
    {"buyer": "A", "supplier": "B", "product": "wafer", "amount": 80, "period": "2026"},
    {"buyer": "A", "supplier": "C", "product": "wafer", "amount": 20, "period": "2026"},
    {"buyer": "A", "supplier": "B", "product": "gas", "amount": 50, "period": "2026"},
    {"buyer": "D", "supplier": "A", "product": "chip", "amount": 40, "period": "2026"},
    {"buyer": "E", "supplier": "B", "product": "wafer", "amount": 10, "period": "2026"},
]


def _demo():
    edges, dropped = clean_edges(SAMPLE)
    assert dropped == []
    report = analyze(edges, threshold=1.0, failed=["B"], max_depth=3)
    hhi = {(r["buyer"], r["product"]): r["hhi"] for r in report["concentration"]}
    assert abs(hhi[("A", "wafer")] - 0.68) < 1e-9
    assert abs(hhi[("A", "gas")] - 1) < 1e-9
    singles = {(r["buyer"], r["product"], r["supplier"]) for r in report["single"]}
    assert singles == {("A", "gas", "B"), ("D", "chip", "A"), ("E", "wafer", "B")}
    affected = [(r["id"], r["depth"], r["lost"]) for r in report["propagation"]["affected"]]
    assert affected == [("A", 1, 130.0), ("E", 1, 10.0), ("D", 2, 40.0)]
    assert [r["supplier"] for r in alternatives(edges, "wafer", exclude={"B"})] == ["C"]
    assert validate(edges, report, failed=["B"]) == []
    broken = analyze(edges, failed=["B"])
    broken["concentration"][0]["hhi"] = 0.1
    assert validate(edges, broken, failed=["B"]) != []
    # 비중 0.8 과 같으면 단일 공급에 포함한다
    assert any(r["supplier"] == "B" and r["product"] == "wafer" for r in single_source(edges, 0.8))
    nx = degree_centrality_nx(edges)
    if nx is not None:
        for node, row in report["centrality"].items():
            assert abs(nx[node]["in"] - row["in"]) < 1e-9
            assert abs(nx[node]["out"] - row["out"]) < 1e-9
    print("HHI A/wafer", round(hhi[("A", "wafer")], 2), "A/gas", round(hhi[("A", "gas")], 2))
    print("단일 공급(기준 1)", sorted(singles))
    print("B 중단", affected)
    print("wafer 대체처(B 제외)", alternatives(edges, "wafer", exclude={"B"}))
    print("OK")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    _demo()
