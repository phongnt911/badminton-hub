from pathlib import Path
import json,re
root=Path('/workspace/badminton-hub');out=Path('/workspace/scratch/bh07-review-c8a8e7f');private=Path('/tmp/bh07-http-review-runtime')
p=(root/'scripts/bh07_browser/run_browser_verification.js').read_text();anon=json.loads((private/'kong.json').read_text())['consumers'][0]['keyauth_credentials'][0]['key']
p=p.replace("const CHROME_PATH = 'C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe';","const CHROME_PATH = '/usr/bin/chromium';")
p=p.replace("const PROJECT_ROOT = path.resolve(__dirname, '../..');","const PROJECT_ROOT = '/workspace/badminton-hub';")
p=p.replace("const EVIDENCE_DIR = path.resolve(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence');","const EVIDENCE_DIR = '/workspace/scratch/bh07-review-c8a8e7f/browser';")
p=p.replace("    '--headless=new',","    '--headless=new',\n    '--no-sandbox',")
p=p.replace("  execSync('node scripts/bh07_browser/seed_setup.js', { stdio: 'inherit' });","  log('Reviewer infrastructure: identical SQL fixture already seeded in isolated stack');")
p=re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',lambda _:anon,p)
(private/'browser_runner.js').write_text(p)
print('Prepared infrastructure-only runner adaptation; assertions unchanged')
