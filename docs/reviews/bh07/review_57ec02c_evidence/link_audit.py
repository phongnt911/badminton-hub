import json,re
from pathlib import Path
files=['AGENTS.md','README.md','docs/00_START_HERE.md','docs/09_IMPLEMENTATION_PLAN.md','docs/25_BH07_IMPLEMENTATION_HANDOFF.md','docs/26_BH07_OPERATIONS_REHEARSAL.md','docs/STATUS_HISTORY.md','docs/reviews/bh07/bh07_readiness.md','docs/reviews/bh07/app_profile_heap_handoff.md']
bad=[]
for f in files:
 p=Path(f)
 for n,line in enumerate(p.read_text().splitlines(),1):
  for link in re.findall(r'\]\(([^)]+)\)',line):
   link=link.split('#')[0]
   if link and '://' not in link and not link.startswith('mailto:') and not(p.parent/link).exists():bad.append({'file':f,'line':n,'target':link})
print(json.dumps(bad,indent=2))
