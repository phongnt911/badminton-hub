from pathlib import Path
import json
root=Path.cwd();cap=root/'.build/web-lifecycle-20261113'
s=(root/'scripts/bh07_browser/web_copy_qr_scenario.js').read_text(encoding='utf-8')
e=json.loads((cap/'copy-qr-private-expected.json').read_text(encoding='utf-8'))
assert s.count("const MODE = 'cohost_copy';")==1 and s.count('const EXPECTED_RECEIVER = null;')==1
s=s.replace("const MODE = 'cohost_copy';","const MODE = 'guest_qr';").replace('const EXPECTED_RECEIVER = null;','const EXPECTED_RECEIVER = '+json.dumps(e,ensure_ascii=False)+';')
(cap/'guest-qr-driver.js').write_text(s,encoding='utf-8')
print('Guest QR ignored driver ready; no receiver values printed')
