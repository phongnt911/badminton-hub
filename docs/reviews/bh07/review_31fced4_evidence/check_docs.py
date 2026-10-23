"""Read-only local Markdown path and commit audit for readiness review."""
from pathlib import Path
from urllib.parse import unquote,urlsplit
import re,json,subprocess
ROOT=Path(__file__).resolve().parents[4]
BASE='fdf7113ff46517a4c148fbcfcce5fea960686481'
REVIEWED='31fced4e7f88517bfe86406bce217b058350db1b'
files=subprocess.check_output(['git','diff','--name-only',BASE+'..'+REVIEWED],cwd=ROOT,text=True).splitlines()
links=[];bad=[]
for name in files:
 p=ROOT/name;fenced=False
 for n,line in enumerate(subprocess.check_output(['git','show',REVIEWED+':'+name],cwd=ROOT,text=True).splitlines(),1):
  if re.match(r'^\s*(```|~~~)',line):fenced=not fenced;continue
  if fenced:continue
  for match in re.finditer(r'!?\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)',line):
   target=match.group(1).strip('<>');u=urlsplit(target)
   if u.scheme or target.startswith('#'):continue
   path=unquote(u.path);dest=(p.parent/path).resolve() if not path.startswith('/') else ROOT/path.lstrip('/')
   item={'file':name,'line':n,'target':target,'exists':dest.exists()};links.append(item)
   if not item['exists']:bad.append(item)
text=subprocess.check_output(['git','show',REVIEWED+':docs/reviews/bh07/bh07_readiness.md'],cwd=ROOT,text=True);section=text.split('## 7.')[1].split('## 8.')[0];shas=sorted(set(re.findall(r'\b[0-9a-f]{40}\b',section)))
missing=[s for s in shas if subprocess.run(['git','cat-file','-e',s+'^{commit}'],cwd=ROOT,capture_output=True).returncode]
changed_runtime=[f for f in files if re.match(r'^(lib|test|supabase|scripts)/|^docs/reviews/bh07/.*_evidence/',f)]
print(json.dumps({'files':files,'links_checked':len(links),'missing_links':bad,'section7_commit_count':len(shas),'missing_commits':missing,'unexpected_runtime_evidence_changes':changed_runtime,'path_verdict':'ALL_LINKS_OK' if not bad else 'MISSING_LINKS','sha_verdict':'ALL_COMMITS_OK' if not missing else 'MISSING_COMMITS'},indent=2,ensure_ascii=False))
assert not bad and not missing and not changed_runtime
