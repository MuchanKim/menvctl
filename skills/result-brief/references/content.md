# Result brief content

## Shared contract

A brief lets the reviewer inspect the agent's understanding and verify delivery. File lists and commit summaries are supporting material, not the conclusion. Keep stable requirement IDs (`R1`, `R2`) across both briefs. Record the source and version/date of the agreed requirements; do not silently rewrite the original criteria after implementation. List additions, removals and changed criteria with their source of authorization. A later result may link to the planning brief but must restate the criteria needed to review it independently.

If no planning brief exists, recover requirements from the actual user request or project specification and cite that source. Do not retroactively invent an agreement. Mark unspecified acceptance criteria as unconfirmed and avoid an overall completion claim. Never interpret missing evidence as a pass, failure, or lack of defects.

## Result brief

Order: factual outcome → before/after → requirement results → mandatory review points → performed verification/measurements → merge conditions. Diff/commit tabs follow as supporting evidence. Required IDs: `changes`, `requirements`, `review-focus`, `verification`, `merge-checklist`.

### Facts and traceability

Use `assets/example/content.html`. Report actual actions and observations only. Do not include speculative explanations, invented design rationale, estimated gains or unsupported likelihood/severity scores. A documented design decision may be quoted with its source; a new proposal belongs in a separate **후속 제안 · 미수행** area, never in performed work or acceptance evidence. Known limitations and rollback prerequisites must cite observed changes or documented constraints. Do not infer runtime behavior from a successful compilation.

| Claim | Evidence needed |
|---|---|
| Code was changed | relevant diff/path and precise statement of the change |
| Behavior was verified | scenario, assertions/observations, target revision/tree, environment, command/steps, time, result |
| A defect was fixed | observed reproduction and the relevant post-change check; state which environments remain untested |
| Performance changed | real before/after measurements under comparable conditions; environment, workload/data size, sample count, metric/unit, aggregation and raw result source |
| Requirement was satisfied | the agreed criterion and evidence that addresses that criterion, not just a related implementation |

Use `미실행`, `미측정`, `미검증`, `커버리지 미확인` precisely. Do not estimate numbers to fill a table. When no measurements were taken, say so; do not manufacture a performance section full of guessed values. Show observed before/after values and the calculation for any percentage claim. Disclose different devices/build settings/datasets; noncomparable measurements cannot support a causal improvement claim. A code optimization can be reported as a code change even when its runtime impact is unknown.

The requirement table separates **implementation state** (`구현됨 / 일부 구현 / 미구현 / 확인 불가`) from **verification state** (`통과 / 실패 / 미실행 / 미확인`). Include the criterion, evidence reference and remaining work per row. Any summary count must follow the rows; scope exclusions and changed criteria remain visible.

### Mandatory reviewer attention

Each item has a stable ID, related requirement/criterion, the exact behavior changed, **why review is required and its source**, a diff/path link, the question to answer and the observable acceptance condition. Show existing verification separately from the unresolved reviewer judgment.

Do not write only “check error handling” or “review concurrency.” For example: “R2 requires unidentified messages to remain unassigned; inspect the fallback assignment branch at this diff and confirm no suspect ID is assigned on parse failure.” This is a review request, not a claim that the failure exists.

Only mark items **필수** when required by an agreed criterion, repository rule or explicit review instruction. Agent-suggested review points are **제안**, with rationale. Do not invent merge blockers from speculative risk. If no extra human review item was identified, say so with the inspected scope; do not claim independent approval.

### Verification and manual tests

Executed checks need command/steps, environment/device/OS/build configuration, date/time, exact target, exit/result, evidence reference and limitations. Record self-review as self-review. If later edits invalidate earlier evidence, mark it stale or rerun; never silently carry it forward.

Future manual/device tests belong in a separate **미수행 · 사용자 확인** section. Each item specifies requirement ID, required/recommended basis, preparation, environment, action sequence, expected result, explicit failure condition and what evidence to record. Perform available automated checks first; do not transfer agent-verifiable work to the reviewer without an actual limitation.

### Merge checklist

A merge checklist is a status table, not an automatically checked approval form. Each row includes condition ID, criterion/rule source, mandatory/proposed classification, `충족 / 미충족 / 미확인 / 해당 없음`, evidence or remaining work, and the verifier/time where relevant. `해당 없음` requires a reason. For a report not associated with merging, keep the section and explain why it does not apply rather than request a merge decision.

Typical conditions, **only when applicable and sourced**: agreed acceptance criteria, required automated checks, required device tests, mandatory review points, unresolved recorded blockers, and documented compatibility/deployment/rollback prerequisites. No universal mandatory device test, second reviewer, or performance threshold is implied.

Human review/approval is recorded only from an actual person's review record, including actor, time and scope. The agent cannot mark human review complete, or infer it from passing tests, a file-overlap check, a local checkbox, or acceptance of the implementation plan. A report may summarize unresolved required conditions but must not fabricate permission to merge or perform the merge.

Every non-header table row inside `#merge-checklist` is a condition row and must include `data-check-kind`, `data-verdict` and `data-basis`. Use an explicit `<thead>` for headers. When merging does not apply, retain the section with an explanatory paragraph and no table. Machine validation checks metadata presence, not truth:

```html
<tr data-check-kind="criterion" data-verdict="unknown" data-basis="R1 / acceptance A1"><td>A1</td><td>미확인</td><td>실기기 검증 미실행</td></tr>
<tr data-check-kind="automated" data-verdict="met" data-basis="repository rule" data-evidence="logs/test-run.txt"><td>자동 테스트</td><td>충족</td><td>명령·대상·환경·결과를 본문에 기재</td></tr>
<tr data-check-kind="criterion" data-verdict="na" data-basis="scope" data-reason="No merge requested"><td>머지</td><td>해당 없음</td><td>보고서 전용 작업</td></tr>
```

`data-check-kind` must be `human` (a person’s review or approval), `automated` (an executed automated check), or `criterion` (other acceptance conditions). Do not classify a human approval as a criterion to bypass its required record. `met` requires `data-evidence`; every row requires `data-basis`; `na` requires `data-reason`. A `human` row with `met` also requires `data-actor` and `data-time`. Use the same status in the visible table and attributes: `met` = 충족, `unmet` = 미충족, `unknown` = 미확인, `na` = 해당 없음. These are references to visible evidence, not substitutes for it. The builder cannot establish whether a source actually exists or supports a claim. Author/reviewer inspection remains required.
