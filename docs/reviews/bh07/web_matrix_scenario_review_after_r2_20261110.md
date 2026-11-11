# Web matrix review after correction2 — 10/11/2026

**Chưa đạt; giao sửa vòng3/3.** Anti conversation `b96ce0d9-58f5-4efd-966a-623b7aa45c5e` completed SUCCESS. WM2 cleanup source control now rejects setOffline failure and positive cleanup succeeds; listeners are removed in nested finally. Original count/member-money negative controls reject and positive controls pass.

- **WM4 P2 remains:** actual response predicate accepts missing p_session_id, invalid JSON and wrong local API port. Source-extracted predicate controls: valid=true, missingSession=true, invalidJson=true, wrongSession=false, OPTIONS=false, wrongPort=true. Require correct request body session ID and exact local API origin; malformed/missing data must reject. Scope is the real UI-triggered POST, not a direct API replacement.
- **WM5 P2 — CLI expression contract:** script ends with `};`. Node --check accepts that as a statement, but CLI wraps file text in parentheses as a single function expression and fails `SyntaxError: Unexpected token ';'`. Root real Edge wrong-due control stopped at parse time (`.build/web-matrix-capture/edge-wrong-due.log`); it is NOT an aggregate-oracle rejection or Edge PASS. Remove trailing statement semicolon and verify expression wrapping, not only standalone Node syntax.
- Minor accuracy: console classifier labels any net:: error as offline even if a QR resource failure; keep generic/known categories honest. Handoff must use distinct named Edge/Firefox sessions, rather than successive default browser opens.

SC1 schema portability is independently accepted and pushed1717451; no further Dart change needed. Firefox separate investigation: public deep-link semantics load, but page screenshot white while separate HTML diagnostic page paints correctly. Do not call the Firefox visual test PASS based solely on its accessibility tree. No app cause established yet.

After third correction handoff Codex directly fixes concrete residual bugs under standing owner authorization. Full V2/V2b/BH-07/V8 remains unaccepted.
