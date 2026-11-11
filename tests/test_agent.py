"""재분석 에이전트. 네트워크를 부르지 않는다."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "templates" / "agent"))
sys.path.insert(0, str(ROOT / "tools"))

import graph_ref as g  # noqa: E402
import reanalyze as r  # noqa: E402


class AgentTest(unittest.TestCase):
    def test_rules(self):
        cond, via = r.parse_request("거래처 B 부도", allow_env=False)
        self.assertEqual(via, "rule")
        self.assertEqual(cond, {"type": "supplier_failure", "company_id": "B"})
        cond, _ = r.parse_request("국가 ZZ 수출통제", allow_env=False)
        self.assertEqual(cond["country"], "ZZ")
        cond, _ = r.parse_request("wafer 단가 상한 1,000", allow_env=False)
        self.assertEqual(cond["max_unit_price"], 1000.0)

    def test_unknown_sentence(self):
        with self.assertRaises(ValueError):
            r.parse_request("단가 상한 변경", allow_env=False)

    def test_rule_skips_llm(self):
        called = []

        def llm(text):
            called.append(text)
            return "{}"

        _, via = r.parse_request("거래처 B 부도", llm=llm, allow_env=False)
        self.assertEqual(via, "rule")
        self.assertEqual(called, [])

    def test_llm_checked(self):
        def bad(_text):
            return '{"type":"drop_all"}'

        with self.assertRaises(ValueError):
            r.parse_request("문을 닫았다", llm=bad, allow_env=False)

        def good(_text):
            return '```json\n{"type":"supplier_failure","company_id":"B"}\n```'

        cond, via = r.parse_request("문을 닫았다", llm=good, allow_env=False)
        self.assertEqual(via, "llm")
        self.assertEqual(cond["company_id"], "B")

    def test_failure_diff(self):
        companies = {"B": {"country": "ZZ"}, "C": {"country": "KR"}}
        result = r.reanalyze(g.SAMPLE, companies, {"type": "supplier_failure", "company_id": "B"})
        self.assertEqual(result["diff"]["added"], [("A", "wafer", "C")])
        self.assertEqual(result["diff"]["removed"], [("A", "gas", "B"), ("E", "wafer", "B")])
        country = r.reanalyze(g.SAMPLE, companies, {"type": "country_control", "country": "ZZ"})
        self.assertEqual(country["diff"], result["diff"])
        self.assertIn("추가 A / wafer / C", r.explain(result))
        # 원본 표본은 그대로다.
        self.assertEqual(len(g.SAMPLE), 5)

    def test_price_cap_equal_kept(self):
        # 단가 2000 은 상한 2000 이면 유지, 상한 1000 이면 제거.
        rows = [
            {"buyer": "A", "supplier": "B", "product": "wafer", "amount": 2000, "period": "2026", "qty": "1"},
            {"buyer": "A", "supplier": "C", "product": "wafer", "amount": 500, "period": "2026", "qty": "1"},
        ]
        kept, _, note = r.apply_rows(rows, {}, {"type": "price_cap", "product": "wafer", "max_unit_price": 2000})
        self.assertEqual(sorted(row["supplier"] for row in kept), ["B", "C"])
        self.assertEqual(note["skipped_no_qty"], 0)
        result = r.reanalyze(rows, {}, {"type": "price_cap", "product": "wafer", "max_unit_price": 1000})
        self.assertEqual(result["diff"]["added"], [("A", "wafer", "C")])

    def test_example_json(self):
        obj = json.loads((ROOT / "templates" / "agent" / "conditions.example.json").read_text(encoding="utf-8"))
        self.assertEqual(r.validate_condition(obj)["type"], "supplier_failure")

    def test_cli(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "templates" / "agent" / "reanalyze.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK", proc.stdout)


if __name__ == "__main__":
    unittest.main()
