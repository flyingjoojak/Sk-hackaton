# 조건 재분석 (최소)

자연어 한 줄을 조건 JSON 으로 바꾼 뒤, 거래 그래프의 단일 공급 집합이 어떻게 달라졌는지만 보여 준다. 숫자는 `tools/graph_ref.py` 가 계산한다. LLM 은 규칙이 실패하고 `OPENAI_API_KEY` 가 있을 때만 쓴다. 키가 없으면 규칙만 쓴다.

허용 type:

| type | 필수 키 | 하는 일 |
|---|---|---|
| supplier_failure | company_id | 그 공급자의 간선을 제거 |
| country_control | country | 국가가 정확히 같은 공급자의 간선을 제거. 빈 국적은 제외하지 않음 |
| price_cap | product, max_unit_price | 그 자재의 단가(amount/qty)가 상한보다 큰 행을 제거. 같으면 유지. qty 가 없으면 행을 유지하고 보고서에 센다 |

```
python3 templates/agent/reanalyze.py
```

네트워크와 API 키 없이 예시 문장 두 개(`거래처 B 부도`, `국가 ZZ 수출통제`)를 돌리고 `OK` 를 찍는다.
