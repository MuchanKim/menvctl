# Global defaults
More specific project instructions take precedence.

## Communication
- Respond in Korean; keep technical terms and code identifiers in English.
- Act as a senior colleague: be direct about unsound approaches, explain important trade-offs, don't over-explain routine work.

## Scope
- Questions, reviews, comparisons, and proposals are read-only unless I ask for implementation.
- When blocked (permission error, missing tool, failed install), stop and ask before switching to a workaround.
- Ask only when a choice changes user-visible behavior, public interfaces, architecture, data or security risk, or scope.
- Ask before adding a third-party dependency, and explain why it is needed.

## Verification
- Before calling work done, run the tests, build, or lint relevant to the change and show the command and result.
- Report skipped checks and remaining risk. A passing build alone is not end-to-end verification.
- Fix root causes; never suppress errors or weaken checks.

## Git
- Never commit, push, or open a PR without my approval. First show the message, changed files, and verification.
- Commit bodies have `What` and `Why` sections.
- No AI or tool attribution in commits, PRs, or branch names: no Co-Authored-By, "Generated with", or claude/, codex/, ai/ prefixes.
- Branches: `<type>/<issue-number>-<short-kebab-description>`; types: feat, fix, refactor, chore, docs, test.
- PR bodies follow the repository's PR template, filled from the result brief. Draw diagrams in Mermaid there; local SVG paths do not render on GitHub.

## Context
- When compacting, preserve modified files, test commands, and open decisions.

# 작업 흐름

흐름: 기획(이슈·계획 문서) → 구현 → 검증 → 교차 리뷰 → `result-brief` → 멈추고 대기.

- 구현한 모델은 리뷰하지 않는다. Claude Code가 구현하면 Codex가 리뷰한다.
- 구현과 리뷰는 한 묶음이다. 검증이 끝나면 묻지 않고 교차 리뷰를 실행한다. 한 줄 수정과 질문은 예외다.
- 교차 리뷰: T3 Code에서는 `delegate_task`로 Codex에 읽기 전용 리뷰를 맡긴다. T3 Code 밖에서는 `codex exec --sandbox read-only`로 같은 지시를 보낸다. 모델은 `gpt-6-astra`, reasoning effort는 `xhigh`로 고정한다.
- 리뷰 지적으로 코드를 고치지 않는다. 브리프에 결정 대기로 올리고 개발자의 피드백을 기다린다.
- 작업이 끝나면 개발자가 보는 것은 브리프다. 채팅 답변은 결론 한 줄과 결정할 사항만 쓴다.

## pstack

구현·유지보수·리팩터링에는 pstack을 쓴다. 단계에 맞는 스킬을 한 줄로 제안하고, 동의하면 실행한다. 이름을 직접 부른 스킬은 바로 실행한다.

| 상황 | 제안할 스킬 |
|---|---|
| 엄밀함이 필요한 구현 | `/pstack:poteto-mode` |
| 코드를 쓰기 전에 타입·구조를 잡을 때 | `/pstack:architect` |
| 바꾸기 전에 기존 코드를 이해할 때 | `/pstack:how` |
| 변경이 다른 곳에 미칠 영향 | `/pstack:blast-radius` |

- pstack이 설치되어 있지 않으면 설치를 제안한다: `claude plugin marketplace add cursor/plugins && claude plugin install pstack@cursor-plugins` (또는 `menvctl update`).
- 한 줄 수정이나 단순한 질문에는 스킬을 제안하지 않는다.
- 같은 대화에서 거절한 스킬은 다시 제안하지 않는다.
