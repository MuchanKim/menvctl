# Planning HTML structure

The body contains one or more `.tab-page` elements. Overview is required. Its sections must have IDs `requirements`, `scenarios`, `acceptance`, and `decisions`; use `data-toc` for sidebar labels. Start from `assets/example/content.html` and follow [content.md](content.md) for each table's fields.

```html
<div class="tab-page" data-tab="overview" data-label="기획 개요">
  <header class="hero"><h1>Title</h1></header>
  <section id="requirements" data-toc="요구 이해"><h2>요구 이해</h2></section>
  <section id="scenarios" data-toc="시나리오"><h2>시나리오</h2></section>
  <section id="acceptance" data-toc="완료 기준"><h2>완료 기준</h2></section>
  <section id="decisions" data-toc="결정 사항"><h2>결정 사항</h2></section>
</div>
```

Use the template's `.card`, `.grid`, `.meta`, `.pill` styles. No diff embeds, file browser, actual-change statistics or commit tabs are allowed. Proposed verification is not an execution result. This builder does not inspect Git and does not require a repository.

Body HTML is trusted authored input. Keep it self-contained: no executable body scripts or external fonts/scripts/images/styles. Escape untrusted text. Inline SVG is allowed for mechanisms that need a diagram.

The builder rejects duplicate IDs, dangling internal links, missing sections and scaffold markers (`data-placeholder` or the explicit token `[REPLACE]`). Do not remove a marker without replacing its instructional content. `--draft` allows content issues with a visible warning and is not approval-ready. Hard argument/path failures still fail. Normal failures exit 2 and preserve an older report; do not mistake it for new output.

Local checkboxes, when used, need unique stable `data-check-id` values. Their saved state is tied to the report fingerprint. They are personal notes, not approval or execution evidence. Avoid using them for accepting a plan on behalf of a person.

Browser QA requires `window.reviewBriefValidation.ready === true`, empty `.errors`, no unresolved embeds, and no console errors. Inspect all tabs, layout, theme and navigation. The optional `scripts/check_browser.mjs` uses an existing Playwright installation; `REVIEW_BRIEF_PLAYWRIGHT` may point to its module entry and `REVIEW_BRIEF_BROWSER` to Chromium/Chrome. It installs nothing. When unavailable, explicitly report browser verification as unexecuted.

The final HTML must not contain duplicate IDs. Body IDs must not reuse template IDs such as `main`, `diff-data`, `toc-list`, `theme-btn` or `wrap-btn`. Use distinct section IDs. Input and output must refer to different files, including through symlinks or `..` path aliases.
