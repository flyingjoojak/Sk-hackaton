---
name: verify
description: 제출 전 최종 확인. 테스트 전체 실행, 실제 실행, TASK.md 완료 조건 대조, 제출물 형식, README 정리, preflight. "제출 전 확인", "검증해줘"에 사용.
---

# verify

말이 아니라 실행 결과로 확인한다. 각 항목에 명령과 결과를 붙이고 상태는 PASS / FAIL / NOT_RUN / HUMAN_CHECK 로만 쓴다.

1. 테스트 전체: `python3 -m pytest -q` (또는 과제가 정한 방법). 실패가 있으면 멈추고 보고.
2. 실제 실행: 과제가 요구한 방식 그대로 돌리고 출력 일부를 보여준다.
3. 완료 조건 대조표: 조건 / 테스트 이름 / 상태. `TASK.md` 5번 표를 갱신한다.
4. 핵심 숫자는 다른 방법(다른 코드 경로, 손계산 가능한 작은 표본)으로 한 번 더 맞춘다.
   - 과제가 Docker 실행을 요구하면: README 의 명령 그대로 `docker build` 와 `docker run` 을 새로 해서 뜨는지, 포트와 데이터 경로가 맞는지 확인한다. Docker 를 쓸 수 없는 환경이면 NOT_RUN 으로 적고 이유를 남긴다.
5. 제출물 형식: 파일명, 경로, 열 이름, 인코딩, 정렬, 개수.
6. README 를 심사자가 읽는 순서로 정리한다(항목마다 세 줄 이내):
   - 무엇을 만들었나 / 무엇을 자동화했고 무엇은 하지 않았나 / 실행 방법(실제로 쳐 본 명령만) / 현재 상태(숫자) / 내가 정한 것과 이유 / 하지 못한 것과 이유
7. `python3 ~/sk-hackaton/scripts/preflight.py submit` 실행. exit 0 이 아니면 이유를 적는다.
8. 과제가 요구한 기록 파일(예: `AI_COLLABORATION.md`)이 있고, 디버깅 4칸이 실제 커밋, 실행 결과와 맞는지.
9. 남은 것: `TODO`, 디버그 출력, 임시 파일, 비밀값, `git status` 미커밋.

## 출력
```
PASS N / FAIL N / NOT_RUN N / HUMAN_CHECK N
FAIL, NOT_RUN, HUMAN_CHECK 은 이유와 남은 위험을 한 줄씩.
```
