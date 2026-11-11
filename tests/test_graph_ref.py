"""graph_ref 손계산 표본. 기대값은 함수를 부르기 전에 적어 둔다."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import graph_ref as g  # noqa: E402


def edges():
    cleaned, dropped = g.clean_edges(g.SAMPLE)
    return cleaned, dropped


class GraphRefTest(unittest.TestCase):
    def test_hhi_hand(self):
        # 80과 20. 0.8^2 + 0.2^2 = 0.68. 50:50 이면 0.5.
        cleaned, _ = edges()
        rows = {(r["buyer"], r["product"]): r for r in g.concentration(cleaned)}
        self.assertAlmostEqual(rows[("A", "wafer")]["hhi"], 0.68)
        self.assertAlmostEqual(rows[("A", "gas")]["hhi"], 1.0)
        half, _ = g.clean_edges([
            {"buyer": "A", "supplier": "B", "product": "x", "amount": 50, "period": "2026"},
            {"buyer": "A", "supplier": "C", "product": "x", "amount": 50, "period": "2026"},
        ])
        self.assertAlmostEqual(g.concentration(half)[0]["hhi"], 0.5)

    def test_threshold_equal_included(self):
        # 비중 0.8 은 기준 0.8 에 포함, 0.79 는 제외.
        cleaned, _ = edges()
        hit = g.single_source(cleaned, 0.8)
        self.assertIn(("A", "wafer", "B"), {(r["buyer"], r["product"], r["supplier"]) for r in hit})
        below, _ = g.clean_edges([
            {"buyer": "A", "supplier": "B", "product": "wafer", "amount": 79, "period": "2026"},
            {"buyer": "A", "supplier": "C", "product": "wafer", "amount": 21, "period": "2026"},
        ])
        keys = {(r["buyer"], r["product"], r["supplier"]) for r in g.single_source(below, 0.8)}
        self.assertNotIn(("A", "wafer", "B"), keys)

    def test_propagate_depth_and_cycle(self):
        cleaned, _ = edges()
        deep = g.propagate(cleaned, ["B"], max_depth=3)
        self.assertEqual(
            [(r["id"], r["depth"], r["lost"]) for r in deep["affected"]],
            [("A", 1, 130.0), ("E", 1, 10.0), ("D", 2, 40.0)],
        )
        # 깊이 상한과 같으면 포함하고, 그보다 깊은 노드는 버린다.
        shallow = g.propagate(cleaned, ["B"], max_depth=1)
        self.assertEqual(sorted(r["id"] for r in shallow["affected"]), ["A", "E"])
        cycle, _ = g.clean_edges([
            {"buyer": "B", "supplier": "A", "product": "p", "amount": 5, "period": "2026"},
            {"buyer": "A", "supplier": "B", "product": "p", "amount": 7, "period": "2026"},
        ])
        got = g.propagate(cycle, ["A"], max_depth=5)
        self.assertEqual([(r["id"], r["depth"]) for r in got["affected"]], [("B", 1)])

    def test_alternatives_and_diff(self):
        cleaned, _ = edges()
        self.assertEqual(
            [r["supplier"] for r in g.alternatives(cleaned, "wafer", exclude={"B", "A"})],
            ["C"],
        )
        before = g.single_source(cleaned, 1.0)
        after_edges = g.without_suppliers(cleaned, ["B"])
        after = g.single_source(after_edges, 1.0)
        self.assertEqual(g.diff_single(before, after)["added"], [("A", "wafer", "C")])
        self.assertEqual(
            g.diff_single(before, after)["removed"],
            [("A", "gas", "B"), ("E", "wafer", "B")],
        )
        # 원본 간선 수는 그대로다.
        self.assertEqual(len(cleaned), 5)

    def test_checker_catches_bad_hhi(self):
        cleaned, _ = edges()
        report = g.analyze(cleaned, failed=["B"])
        self.assertEqual(g.validate(cleaned, report, failed=["B"]), [])
        report["concentration"][0]["hhi"] = 0.1
        self.assertTrue(g.validate(cleaned, report, failed=["B"]))
        report = g.analyze(cleaned, failed=["B"])
        report["propagation"]["affected"][0]["lost"] = 1
        self.assertTrue(any("손실" in err for err in g.validate(cleaned, report, failed=["B"])))

    def test_drop_zero_self_and_keep_input(self):
        raw = [
            {"buyer": "A", "supplier": "A", "product": "x", "amount": 3, "period": "2026"},
            {"buyer": "A", "supplier": "B", "product": "x", "amount": 0, "period": "2026"},
            {"buyer": "A", "supplier": "B", "product": "x", "amount": 4, "period": "2026"},
            {"buyer": "A", "supplier": "B", "product": "x", "amount": 1, "period": "2026"},
        ]
        snapshot = [dict(r) for r in raw]
        cleaned, dropped = g.clean_edges(raw)
        self.assertEqual(raw, snapshot)
        self.assertEqual(sorted(d["reason"] for d in dropped), ["amount<=0", "self"])
        self.assertEqual(cleaned[0]["amount"], 5)

    def test_empty(self):
        self.assertEqual(g.concentration([]), [])
        self.assertEqual(g.single_source([]), [])
        self.assertEqual(g.propagate([], ["B"])["affected"], [])
        self.assertEqual(g.degree_centrality([]), {})

    def test_country_exact(self):
        companies = {
            "B": {"country": "ZZ"},
            "C": {"country": ""},
            "D": {"country": "ZZ"},
        }
        self.assertEqual(g.ids_in_country(companies, "ZZ"), ["B", "D"])
        self.assertEqual(g.ids_in_country(companies, ""), [])

    def test_load_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "companies.csv").write_text(
                "company_id,name,country,industry\nB,가짜소재,ZZ,소재\n",
                encoding="utf-8",
            )
            (root / "transactions.csv").write_text(
                "buyer_id,supplier_id,product,amount,period\nA,B,wafer,\"1,000\",2026\n",
                encoding="utf-8",
            )
            companies, tx = g.load_dir(root)
            self.assertEqual(companies["B"]["country"], "ZZ")
            self.assertEqual(tx[0]["amount"], 1000)

    def test_nx_matches_when_installed(self):
        cleaned, _ = edges()
        pure = g.degree_centrality(cleaned)
        other = g.degree_centrality_nx(cleaned)
        if other is None:
            return
        for node, row in pure.items():
            self.assertAlmostEqual(other[node]["in"], row["in"])
            self.assertAlmostEqual(other[node]["out"], row["out"])

    def test_cli(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "graph_ref.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)

    def test_centrality_hand(self):
        # 노드 5, 분모 4. B 의 구매자는 A,E 두 곳.
        cleaned, _ = edges()
        cen = g.degree_centrality(cleaned)
        self.assertAlmostEqual(cen["B"]["out"], 0.5)
        self.assertAlmostEqual(cen["A"]["in"], 0.5)


class PeekTest(unittest.TestCase):
    def test_peek_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.csv"
            path.write_text("id,amount\nA,1\nB,\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "peek.py"), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("행 2", proc.stdout)


class PreflightTest(unittest.TestCase):
    def test_env_exit_zero(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "preflight.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("[PASS] python", proc.stdout)


if __name__ == "__main__":
    unittest.main()
