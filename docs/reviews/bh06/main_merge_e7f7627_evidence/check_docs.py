from pathlib import Path
import re,json,subprocess,urllib.parse,unicodedata
root=Path.cwd()
changed=subprocess.check_output(['git','diff','--name-only','e7f7627'],cwd=root,text=True).splitlines()
files=[root/p for p in changed if p.endswith('.md')]
files += [root/'docs/25_BH07_IMPLEMENTATION_HANDOFF.md',root/'docs/reviews/bh06/main_merge_e7f7627.md']
files=list(dict.fromkeys(files));errors=[];count=0;fragments=0

def headings(p):
 s=re.sub(r'```.*?```','',p.read_text(),flags=re.S)
 ids=set(re.findall(r'<a\s+(?:id|name)="([^"]+)"',s));counts={}
 for line in s.splitlines():
  m=re.match(r'^#{1,6}\s+(.+?)\s*#*$',line)
  if not m:continue
  h=re.sub(r'<[^>]*>','',m.group(1));h=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',h)
  slug=re.sub(r'[^\w\- ]','',unicodedata.normalize('NFC',h.lower())).replace(' ','-')
  n=counts.get(slug,0);counts[slug]=n+1
  ids.add(slug+('-'+str(n) if n else ''))
 return ids
for p in files:
 body=re.sub(r'```.*?```','',p.read_text(),flags=re.S)
 for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)',body):
  target=target.strip('<>')
  if re.match(r'^[a-zA-Z][\w+.-]*:',target):continue
  path,_,fragment=urllib.parse.unquote(target).partition('#')
  dest=p.parent/path if path else p
  count+=1
  if not dest.exists(): errors.append({'file':str(p.relative_to(root)),'target':target,'reason':'missing file'});continue
  if fragment and dest.suffix=='.md':
   fragments+=1
   if re.fullmatch(r'L\d+(?:-L\d+)?',fragment): continue
   if fragment not in headings(dest):errors.append({'file':str(p.relative_to(root)),'target':target,'reason':'missing fragment'})
x={'updated_markdown_files':len(files),'relative_links_checked':count,'fragments_checked':fragments,'broken':errors}
(root/'docs/reviews/bh06/main_merge_e7f7627_evidence/doc-check.json').write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(x,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
