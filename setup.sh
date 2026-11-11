#!/usr/bin/env bash
# 과제 폴더에서 실행: bash ~/sk-hackaton/setup.sh
# 과제 AGENTS.md 가 없으면 지침과 스킬을 복사하고 git 에서 숨긴다(방법 A).
# 있으면 건드리지 않고 경로로 읽는 첫 프롬프트를 알려준다(방법 B).
# 어느 경우든 기존 파일은 덮어쓰지 않는다.
# 원본 흐름: https://github.com/flyingjoojak/codex-harness (MIT)
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"

if [ "$(pwd)" = "$KIT" ]; then
  echo "하네스 폴더가 아니라 과제 폴더에서 실행하세요."; exit 1
fi

git rev-parse --git-dir >/dev/null 2>&1 || { git init -q; echo "git 저장소가 없어 git init 했습니다."; }
# 커밋 작성자가 비어 있으면 이 과제 폴더에만 설정한다(전역 설정은 건드리지 않음)
GIT_NAME_SET=""
if [ -z "$(git config user.name || true)" ]; then git config user.name "flyingjoojak"; GIT_NAME_SET=1; fi
if [ -z "$(git config user.email || true)" ]; then git config user.email "flyingjoojak@users.noreply.github.com"; GIT_NAME_SET=1; fi
cp -n "$KIT/TASK.md" "$KIT/DECISIONS.md" "$KIT/UNDERSTANDING.md" . 2>/dev/null || true
EXCLUDE="$(git rev-parse --git-path info/exclude)"
mkdir -p "$(dirname "$EXCLUDE")"
grep -qx '.pytest_cache/' "$EXCLUDE" 2>/dev/null || printf '__pycache__/
.pytest_cache/
' >> "$EXCLUDE"

# 상세 안내 > 환경 점검 > 방법과 첫 프롬프트 순. 바로 칠 내용이 화면 맨 아래에 오게 한다.
cat "$KIT/GUIDE.txt"
echo
python3 "$KIT/scripts/preflight.py" || true

if [ -e AGENTS.md ]; then
  echo
  echo "[방법 B] 과제에 AGENTS.md 가 이미 있습니다. 건드리지 않았습니다."
  echo "다음 명령: codex --add-dir $KIT"
  echo "첫 프롬프트:"
  echo "  과제 AGENTS.md 가 우선이고, 부딪히지 않는 범위에서 $KIT/AGENTS.md 도 따른다. 스킬은 필요할 때 $KIT/.agents/skills/<이름>/SKILL.md 를 읽어서 쓴다. 적용한 지침을 3줄로 요약한 뒤 dev-flow 1단계부터 시작해. 아직 코드는 쓰지 마."
else
  cp -n "$KIT/AGENTS.md" .
  if [ -e .agents ]; then
    cp -rn "$KIT/.agents/skills" .agents/ 2>/dev/null || true
  else
    cp -r "$KIT/.agents" .
  fi
  grep -qx 'AGENTS.md' "$EXCLUDE" 2>/dev/null || printf 'AGENTS.md\n.agents/\n' >> "$EXCLUDE"
  echo
  echo "[방법 A] AGENTS.md 와 스킬을 복사했고 git 에서 숨겼습니다."
  echo "다음 명령: codex --add-dir $KIT"
  echo "첫 프롬프트:"
  echo "  AGENTS.md 를 따른다. 적용한 지침을 3줄로 요약한 뒤 \$dev-flow 1단계부터 시작해. 아직 코드는 쓰지 마."
fi
echo
if [ -n "$GIT_NAME_SET" ]; then echo "git 작성자가 비어 있어 이 폴더에만 설정했습니다: $(git config user.name) <$(git config user.email)>"; else echo "git 작성자: $(git config user.name) <$(git config user.email)>"; fi
echo "위로 스크롤하면 오늘 할 일 상세 안내가 있다. 다시 보기: cat ~/sk-hackaton/GUIDE.txt"
