# UI sweep — September 2026

This source-level review covered the dashboard and its widgets, application navigation, global search, document cards/list/detail, and user settings. Chat and provider configuration were reviewed and implemented alongside this sweep; see CHAT-PROVIDERS.md. No running UI was available on localhost:4200 and no browser connector was available, so visual contrast, responsive rendering, and real screen-reader behavior still need browser verification.

## Bugs fixed

- **High: stale global-search results and stuck loading.** Older keyword/semantic responses could replace newer results or reopen a dismissed search; keyword errors left the spinner active. Responses now belong to a query generation, closing or editing invalidates old responses, failed keyword searches report an error, and subscriptions end with the component. The dropdown close template now actually invokes its handler. Files: `src-ui/src/app/components/app-frame/global-search/`.
- **Medium: semantic results were inaccessible to arrow-key navigation.** Navigation now counts rendered rows, including semantic-only hits. Moving right stays within the current row instead of incorrectly focusing another row when a saved view has no secondary action. Regression tests cover stale responses, request errors, and semantic-only keyboard navigation.
- **Medium: document selection controls were hidden from keyboard and touch users.** Checkbox overlays are now revealed by keyboard focus, selected state, and touch devices. Checkboxes have accessible names; clicking one emits selection only once. Files: both `document-list/document-card-{small,large}/` directories. Both card suites pass, including bubbling regressions (19 tests).
- **Medium: dashboard statistics could stay loading permanently after a server error.** The widget now clears loading, displays a failure message, and offers a retry. A regression exercises failure and successful retry. Files: `dashboard/widgets/statistics-widget/`.
- **Medium: retrying the same uploaded file did nothing.** The upload input is cleared after files are handed to the upload service, so choosing the same file again triggers change. File: `dashboard/widgets/upload-file-widget/upload-file-widget.component.ts`.
- **Low: mobile navigation announced the wrong expanded state.** `aria-expanded` now follows the actual menu state and the navigation label is localizable. File: `app-frame/app-frame.component.html`.

## Recommended next improvements

1. **Make all document actions keyboard-operable and named at mobile sizes.** Several document-card actions use anchors without `href`, while their text labels are hidden with `d-none d-md-inline`. Convert command actions to buttons and add persistent accessible names. The correspondent filter link is another example. Preserve route links for navigation. Inspect both document-card templates.
2. **Make dashboard statistics filters usable without a mouse.** Filetype bars and legend items are clickable `div` elements without keyboard handlers; use buttons in the legend with visible focus states. Keep progress bars informational. File: `statistics-widget.component.html`.
3. **Give the dashboard's saved-view hint normal text contrast.** `opacity-50` applies to the entire hint, including its link. Use a secondary text color rather than fading all content. File: `dashboard.component.html`.
4. **Keep settings save feedback near the current context.** The long settings form places Save/Cancel at the end. A sticky footer with dirty/saving/saved states would reduce scrolling and make pending edits visible. File: `admin/settings/settings.component.html`.
5. **Improve mobile list scanning.** Keep one primary Open action visible with its label; move infrequent actions to a named overflow menu. Ensure long titles, dense metadata, and tags wrap without pushing actions out of reach. Verify at 320px, 375px, and 768px with long translated labels.
6. **Add a compact browser accessibility matrix.** Exercise desktop/mobile navigation, light/dark themes, reduced motion, keyboard-only document selection, failed API responses, empty archives, and restricted-user permissions. Existing Playwright configuration enables desktop Chromium only; mobile projects are commented out.

## Validation limits

Targeted frontend validation: 99 tests passed across chat/service/widget, document-card, global-search, upload, statistics, and application-configuration suites. TypeScript and Angular template compilation passed. Backend validation: 63 tests passed across providers, client, document chat, agentic search, and chat views. Ruff and whitespace checks passed. Missing local dependencies were restored for these checks; two test fixture type imports were aligned with the installed pytest-django API.

The new migration matches the models and ran in the test database. The active localhost PostgreSQL deployment has since been migrated successfully. The separate legacy SQLite database was left untouched. The public login page passed a headless-browser smoke test; authenticated dashboard/browser verification and live provider calls were not performed.
