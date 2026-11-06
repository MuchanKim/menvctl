---
name: result-brief
description: Report completed code changes as a Markdown reply in the conversation with planned intent versus applied changes (including unplanned changes), before/after SVG diagrams checked by the reviewer, verification and review results, and a user checklist. Use when the user or project requests a result brief, work report or review handoff after implementation. Not for planning proposed work or performing code review itself.
---

# Result Brief

Show what was actually done, as a Markdown reply in the conversation. The diagrams explain the change to the developer; they are the most important part. Use the user's language. Report only changes made and checks run; mark anything not run as `미실행`.

## Order

1. After implementation and before review, draw the diagrams (section 2) and save each as an `.svg` file in a temporary directory outside the repository.
2. Review with a model other than the implementer, without asking, in one read-only call covering code and diagrams (T3 Code `delegate_task`, otherwise `codex exec --sandbox read-only`). The instructions name the SVG files and the base revision and ask, per node and edge, whether it matches the code at its `data-ref` (OK or wrong, with the reason), and what the diagram is missing.
3. Do not change code for review findings; they go into the brief for the developer. Fix diagram errors the reviewer found, and mark each fixed diagram `리뷰 지적으로 수정`.
4. Write the brief and stop. Wait for the developer's feedback before acting on any finding.

## Sections

0. **결론**: one line on the outcome, plus remaining risks.
1. **의도 → 적용**: one row per item of the issue or planning document (linked); without one, use the user's request. Status `적용 / 부분 적용 / 미적용 / 변경됨` and where it landed. Then **기획에 없던 변경**: every change no item explains, with its reason, or `없음`.
2. **Before / After 다이어그램**: hand-drawn SVG files. Draw before from the base revision's code and after from the final code, never from the plan. Use the same layout in both and mark changed nodes and edges with color and a text label. Every node and edge carries `data-ref="path:line"`. Choose the form by what changed: call order or interaction between components → sequence; state transitions → state; type, module or dependency relations → structure; branches or processing steps → flow. If structure and behavior did not change, write `다이어그램 없음: <reason>`. Show the reviewer's verdict under each diagram.
3. **검증 / 리뷰**: commands run and their results, then the reviewer (model) and its findings verbatim, each marked `결정 대기`, with the agent's opinion labeled as such.
4. **사용자 체크리스트**: only what the agent could not verify, such as real devices, UX judgment, external services or real data. Do not repeat checks that already passed. `없음` if nothing remains.

## Output

Write the brief as Markdown in the reply, using tables for sections 1, 3 and 4. Embed each diagram with Markdown image syntax and its absolute `.svg` path. Make the SVG readable in light and dark (`@media (prefers-color-scheme: dark)` inside the SVG). Do not save the brief or the SVGs in the repository. Planning-stage diagrams are drawn only when the developer asks for them.

This skill reports; it does not implement fixes, commit or merge.
