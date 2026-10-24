# Lá»‡nh cháº¡y Ä‘á»™c láº­p V1 (reviewer)

Checkout: `6283dbb3b1ae217e87130acb4ed5efae5bf170c7`, nhÃ¡nh `feat/bh07-browser-independent-review`. Runtime password/JWT/anon key sinh ngáº«u nhiÃªn, lÆ°u ngoÃ i repo (`%TEMP%\bh07-v1-review\private`), khÃ´ng cÃ´ng bá»‘.

## 1. Stack local cÃ´ láº­p

```text
python setup_stack.py
# bh07v1-db / bh07v1-auth / bh07v1-rest / bh07v1-kong trÃªn network bh07v1-net
# gateway 127.0.0.1:55422; 18 migration; seed.sql; fixture UI; 7 user Auth
python seed_fixture.py
```

## 2. Analyze / test / build / web server

```text
flutter analyze                                  # exit 0, 0 issue
flutter test                                     # exit 0, 240 pass + 1 skip
flutter build web --no-pub --no-web-resources-cdn \
  --dart-define=APP_ENV=test \
  --dart-define=SUPABASE_URL=http://127.0.0.1:55422 \
  --dart-define=SUPABASE_ANON_KEY=<runtime-anon-key>   # exit 0
python -m http.server 8088 --bind 127.0.0.1 --directory build/web
```

## 3. Browser tháº­t (Chrome CDP)

```text
python prepare_drivers.py      # táº¡o báº£n sao chá»‰ Ä‘á»•i path/port, xem runner-infra.patch
python seed_fixture.py         # reset fixture trÆ°á»›c baseline
node browser_runner.js         # 11/11 PASS, 12 áº£nh
BH07_BROWSER_DRIVER=<abs>/browser_runner.js \
BH07_LATE_EVIDENCE=<abs>/late node late_runner.js   # 2/2 PASS
```

## 4. Controls (worktree sáº¡ch táº¡i 6283dbb, khÃ´ng ghi vÃ o báº±ng chá»©ng bÃ n giao)

```text
git worktree add --detach <tmp>/controls-wt 6283dbb
node <wt>/scripts/bh07_browser/run_negative_controls.js      # 41/41, exit 0
python <wt>/scripts/bh07_browser/run_verifier_controls.py    # 9/9, exit 0
python <wt>/scripts/bh07_browser/run_mutant_controls.py      # mutant exit 1, exit 0
node <wt>/scripts/bh07_browser/run_late_response_controls.js # 21/21 + 2 mutant, exit 0
```

## 5. Manifest readonly trÃªn báº±ng chá»©ng bÃ n giao

```text
python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/browser_codex_fix_evidence   # 52/52, exit 0
python scripts/bh07_browser/clean_and_manifest.py --verify --evidence-dir docs/reviews/bh07/late_response_evidence      # 44/44, exit 0
git status --porcelain   # rá»—ng trÆ°á»›c vÃ  sau
```

## 6. Manifest cho chÃ­nh gÃ³i báº±ng chá»©ng nÃ y

```text
python scripts/bh07_browser/clean_and_manifest.py --generate --evidence-dir docs/reviews/bh07/review_6283dbb_evidence   # 48 entry, 0 secret
python scripts/bh07_browser/clean_and_manifest.py --verify   --evidence-dir docs/reviews/bh07/review_6283dbb_evidence   # 48/48, exit 0
```
