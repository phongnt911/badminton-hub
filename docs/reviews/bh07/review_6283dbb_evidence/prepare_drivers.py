import json
import re
from pathlib import Path

ROOT = Path(r"C:\Users\POTA\Documents\GitHub\badminton-hub")
OUT = Path(r"C:\Users\POTA\AppData\Local\Temp\bh07-v1-review")
BROWSER_OUT = OUT / "browser"
LATE_OUT = OUT / "late"
BROWSER_OUT.mkdir(parents=True, exist_ok=True)
LATE_OUT.mkdir(parents=True, exist_ok=True)
runtime = json.loads((OUT / "private/runtime.json").read_text(encoding="utf-8"))
api_url = runtime["api_url"]

source = (ROOT / "scripts/bh07_browser/run_browser_verification.js").read_text(encoding="utf-8")
adapted = source
adapted = adapted.replace(
    "} = require('./assertions');",
    f"}} = require({str(ROOT / 'scripts/bh07_browser/assertions.js').replace(chr(92), '/')!r});",
)
adapted = adapted.replace(
    "const CHROME_PATH = 'C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe';",
    "const CHROME_PATH = 'C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe';",
)
adapted = adapted.replace(
    "const PROJECT_ROOT = path.resolve(__dirname, '../..');",
    f"const PROJECT_ROOT = {str(ROOT)!r};",
)
adapted = adapted.replace(
    "const EVIDENCE_DIR = path.resolve(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence');",
    f"const EVIDENCE_DIR = {str(BROWSER_OUT)!r};",
)
adapted = adapted.replace(
    "const dbContainer = 'supabase_db_badminton-hub';",
    "const dbContainer = 'bh07v1-db';",
)
adapted = adapted.replace(
    "    execSync('node scripts/bh07_browser/seed_setup.js', { stdio: 'inherit' });",
    "    log('reviewer infrastructure: fixture pre-seeded against isolated bh07v1 stack');",
)
adapted = adapted.replace(
    "path.resolve(__dirname, 'seed_setup.js')",
    f"path.resolve({str(ROOT / 'scripts/bh07_browser/seed_setup.js')!r})",
)
adapted = adapted.replace(
    "path.resolve(__dirname, 'clean_and_manifest.py')",
    f"path.resolve({str(ROOT / 'scripts/bh07_browser/clean_and_manifest.py')!r})",
)
adapted = adapted.replace(
    "path.resolve(__dirname, 'assertions.js')",
    f"path.resolve({str(ROOT / 'scripts/bh07_browser/assertions.js')!r})",
)
adapted = adapted.replace("api_url: 'http://127.0.0.1:54321',", f"api_url: {api_url!r},")
# Keep the runner's historical BASE_SHA value untouched; mapping is published separately.
(OUT / "browser_runner.js").write_text(adapted, encoding="utf-8")

late_source = (ROOT / "scripts/bh07_browser/run_late_response.js").read_text(encoding="utf-8")
late = late_source
late = late.replace(
    "const { CdpClient, startChrome } = require(process.env.BH07_BROWSER_DRIVER || './run_browser_verification');",
    "const { CdpClient, startChrome } = require(process.env.BH07_BROWSER_DRIVER || './run_browser_verification');",
)
late = late.replace(
    "const A = require('./assertions');",
    f"const A = require({str(ROOT / 'scripts/bh07_browser/assertions.js').replace(chr(92), '/')!r});",
)
late = late.replace(
    "const { validateLateResponse } = require('./late_response_assertions');",
    f"const {{ validateLateResponse }} = require({str(ROOT / 'scripts/bh07_browser/late_response_assertions.js').replace(chr(92), '/')!r});",
)
late = late.replace(
    "const ROOT = path.resolve(__dirname, '../..');",
    f"const ROOT = {str(ROOT)!r};",
)
late = late.replace(
    "path.join(ROOT, 'docs/reviews/bh07/late_response_evidence')",
    f"{str(LATE_OUT)!r}",
)
late = late.replace("http://127.0.0.1:54321/rest/v1/rpc/get_session_summary", f"{api_url}/rest/v1/rpc/get_session_summary")
late = late.replace(
    "verification_mode: 'Codex implementation/self-verification, not independent review'",
    "verification_mode: 'Reviewer/QA run in an isolated local stack; the author of this package did not run this evidence'",
)
(OUT / "late_runner.js").write_text(late, encoding="utf-8")

# Record the infrastructure-only patch for the report/evidence.
patch = f"""Runner adaptation (infrastructure only, no assertion/selector changes)
- baseline driver: absolute assertions path, reviewer evidence dir, DB container bh07v1-db,
  pre-seeded fixture (original seed_setup disabled because Supabase CLI is unavailable on Windows).
- late driver: absolute assertions/assertion path, repo root, reviewer evidence dir,
  API origin {api_url} instead of 54321 because the project local Supabase already owns 54321.
- app/lib/test/supabase source not changed.
"""
(OUT / "runner_adaptation.txt").write_text(patch, encoding="utf-8")
print("prepared drivers")
