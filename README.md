# sk-hackaton

SK hynix AI Hackathon 2026 파이널(개인, 하루, 6시간)을 위한 작업 하네스. 평가 축은 문제 정의, AI 활용, 결과 검증이다. 문제는 현업 담당자의 실제 일에서 나온다.

대비 주제는 **기업 간 거래관계**와 **기업정보 분석**이다. `docs/예상문제.md` 의 10문제는 예측이며 공식 문제가 아니다.

작업 방식은 [codex-harness](https://github.com/flyingjoojak/codex-harness) (MIT, flyingjoojak) 를 옮긴 것이다. 계약 먼저, 증거는 PASS / FAIL / NOT_RUN / HUMAN_CHECK, 결정 로그, 서술형은 사실 > 결정 > 근거 > 한계. 시간만 180분에서 **360분**으로 바꿨다.

## 당일 명령

```
git clone https://github.com/flyingjoojak/Sk-hackaton.git ~/sk-hackaton
cd <과제 폴더>
bash ~/sk-hackaton/setup.sh
codex --add-dir ~/sk-hackaton
```

`setup.sh` 는 과제 폴더에 AGENTS.md 가 없으면 AGENTS.md 와 `.agents/` 를 복사하고 `.git/info/exclude` 로 git 에서 숨긴다. 이미 있으면 과제 파일을 덮어쓰지 않는다. 시간표는 `RUN.md`. 안내를 다시 보려면 `cat ~/sk-hackaton/GUIDE.txt`.

**서술형 답 순서: 사실 > 결정 > 근거 > 한계**

막히면 `pwd`, `ls`, `cat ~/sk-hackaton/GUIDE.txt`. clone 이 already exists 이면 `cd ~/sk-hackaton && git pull`.

## 6시간 안에 만드는 크기

한 사람이 Codex 와 함께 360분 안에 끝내는 구조만 둔다. 그래프는 표준 라이브러리 `dict`(networkx 는 있으면 중심성 대조). 화면은 `templates/app` 의 표준 라이브러리 서버. Neo4j, 크롤러, 학습 모델은 하지 않는다.

MVP 는 CSV 를 읽어 그래프를 만들고, 부도 영향 또는 단일 공급처 표 하나와 검사기 테스트를 내는 것이다. 나머지(HHI, 대체처, 조건 변경 재분석, 화면)는 150분 이후에만. 컷 리스트는 `RUN.md`.

## 구성

```
AGENTS.md                 작업 원칙 (Codex 가 자동으로 읽음)
.agents/skills/
  dev-flow/               읽기 > 계약 > 첫 완주 > 테스트 > 동결 (360분)
  graph-analysis/         거래 그래프: 집중도, 단일 공급처, 전파, 대체처
  systematic-debugging/   근본 원인부터 찾는 4단계
  review-checklist/       정확성, 무음 실패, 보안, 성능, 데이터, 단순성
  verify/                 제출 전 실행 증거 대조
  essay-mock/             서술형 모의
  web-ui/                 웹 화면: 업무 도구답게
  llm-feature/            LLM 호출: 규칙 먼저, 대체 경로, 출력 검증
  data-judge/             표 데이터 판정
TASK.md                   과제 계약 템플릿
DECISIONS.md              결정 로그
UNDERSTANDING.md          이해 문서 (서술형 재료)
RUN.md                    당일 운영표 (360분, MVP 컷)
GUIDE.txt                 setup.sh 가 출력하는 안내
setup.sh                  과제 폴더에서 실행
docs/
  예상문제.md              예측 10문제 (공식 아님)
  거래관계_온톨로지.md     스키마와 조회. 당일은 dict/networkx
  기업분석_알고리즘_대비.md 질문 유형, 알고리즘, 검사기, 서술형
  담당자_인터뷰.md
  서술형_대비.md
  프롬프트.md
  참고자료.md
tools/peek.py             CSV, JSON 구조 훑기
tools/graph_ref.py        거래 그래프 참고 구현과 독립 검사기
scripts/preflight.py      환경 점검, 제출 전 점검 (exit 0 / 1 / 2)
templates/app/            뼈대: 표준 라이브러리 웹 서버, Dockerfile, 테스트
```

연습은 `python3 tools/graph_ref.py` 와 `docs/예상문제.md` 한 문제를 고르는 것으로 한다.

## 점검

```
python3 tools/graph_ref.py
python3 -m unittest discover -s tests -v
python3 scripts/preflight.py
python3 scripts/preflight.py submit
```

종료 코드 0 문제 없음 / 1 문제 있음 / 2 확인한 것이 없음. peek, preflight, graph_ref 는 표준 라이브러리만 필요하다. networkx 가 있으면 차수 중심성을 한 번 더 맞춘다.

## 라이선스

MIT. 작업 흐름과 스킬은 [flyingjoojak/codex-harness](https://github.com/flyingjoojak/codex-harness) (MIT) 를 각색했다. `systematic-debugging` 의 원류는 obra/superpowers-skills (MIT, Jesse Vincent) 이다. 가져온 것과 버린 것은 `docs/참고자료.md`.
