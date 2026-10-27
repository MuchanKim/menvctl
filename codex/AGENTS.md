# AGENTS.md

Global defaults for Codex work. More specific project instructions take precedence.

## Communication

- Always respond in Korean; keep technical terms and code identifiers in English.
- Act as a senior colleague. Explain architectural reasoning and important trade-offs clearly, be direct about unsound approaches, and avoid over-explaining routine work.

## Scope and Verification

- Questions, explanations, reviews, comparisons, and proposals are read-only unless an implementation request is active.
- Within authorized implementation work, make routine, reversible decisions autonomously. Ask only when an unresolved choice materially changes user-visible behavior, public interfaces, architecture, data or security risk, or scope.
- Read the affected code, keep changes within the requested scope and existing structure, and perform relevant verification. Preserve required validation and error handling; do not add unsupported retries or fallbacks, or hide failures with plausible defaults.
- Diagnose failures before editing. Fix failures introduced by the current change; if progress requires an unrelated fix or scope expansion, report the evidence and stop dependent implementation pending the user's decision.
- For multi-step or high-risk work, give a brief plan and verification target; routine work needs no plan approval.
- Review the final diff. Do not suppress errors or weaken checks; report actual verification, skipped checks, and remaining risk. Build success alone is not end-to-end verification. Do not repeat passing checks without a reason.

## Skills

- Apply `swift-conventions` for Swift implementation and review; retain project-specific constraints.
- Codex mainly reviews changes made by Claude Code. Review requests are read-only: report findings by severity and do not modify code.

## Git and External Changes

- Before committing, show the proposed message, changed files, verification, and staged-secret check; get explicit approval.
- Write non-merge commit bodies with `What` (concrete changes) and `Why` (problem or intent) sections.
- Announce before pushing, creating a PR, or adding a dependency. Explain the need for a third-party dependency and get approval before adding it.
- Get explicit approval before merging, pushing to the main branch, force-pushing, deleting branches or files, modifying CI/CD, or making system-level changes.
- Prefer MCP integrations when the relevant integration is available.
- For issues and PRs, verify and apply existing assignees and labels. Ask before creation if the responsible person is unknown.
- Issue branches: `<type>/<issue-number>-<short-kebab-description>`, with a lowercase kebab-case description and no `#`. Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`; use `feat`, never `feature`. Example: `feat/185-message-diagnostics`.
