# Planning brief content

## Shared contract

A brief lets the reviewer inspect the agent's understanding and verify delivery. File lists and commit summaries are supporting material, not the conclusion. Keep stable requirement IDs (`R1`, `R2`) across both briefs. Record the source and version/date of the agreed requirements; do not silently rewrite the original criteria after implementation. List additions, removals and changed criteria with their source of authorization. A later result may link to the planning brief but must restate the criteria needed to review it independently.

If no planning brief exists, recover requirements from the actual user request or project specification and cite that source. Do not retroactively invent an agreement. Mark unspecified acceptance criteria as unconfirmed and avoid an overall completion claim. Never interpret missing evidence as a pass, failure, or lack of defects.

## Planning brief

Order: understanding → scenarios → acceptance criteria → decisions. Required section IDs: `requirements`, `scenarios`, `acceptance`, `decisions` (inside the overview tab).

| Content | Fields |
|---|---|
| Requirements and scope | ID, original request/source, interpretation, included/excluded behavior, confirmation state |
| Scenarios | requirement ID, initial conditions, action, expected behavior, relevant exception path |
| Acceptance criteria | criterion ID, requirement ID, observable pass/fail conditions, planned verification method, required environment |
| Decisions | unresolved question, source of uncertainty, proposal/options and trade-offs, who must decide, whether implementation depends on it |

Distinguish **사용자 요구**, **확인된 사실**, **에이전트 제안**, **미확정 사항** visibly. Minimize assumptions. Only ask when a missing decision materially affects behavior, scope or acceptance; do not add an approval gate for routine implementation details. Proposed criteria are not agreed criteria until confirmed. Forecasts and targets are proposals, never measured results. An empty decision list should say there are no identified decisions, not fabricate a choice.

Use `assets/example/content.html`. Planning must not include actual diff embeds, change statistics, commit tabs or claims of completed verification. Explain proposed changes in prose, tables or inline SVG. The builder does not inspect Git in this mode; cite any repository observations manually if actually inspected. A planning brief is not implementation authorization by itself.

