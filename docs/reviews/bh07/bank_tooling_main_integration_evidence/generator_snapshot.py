"""Review packaging only: export main, apply a scoped patch there, never change refs."""
import ast
import hashlib
import io
import json
import re
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def git(*args):
    p=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,timeout=60)
    if p.returncode: raise RuntimeError('Git inspection failed; diagnostics withheld')
    return p.stdout
SOURCE=git('rev-parse','HEAD').decode().strip()
BASE=git('rev-parse','main').decode().strip()
label=sys.argv[1] if len(sys.argv)>1 else 'v1'
if not re.fullmatch(r'[a-zA-Z0-9_-]+',label):raise SystemExit('invalid package label')
OUT=ROOT/'build'/f'bh07-main-integration-{BASE[:7]}-{SOURCE[:7]}-{label}'
if OUT.exists():raise SystemExit('package exists; refusing overwrite')
OUT.mkdir(parents=True)
CANDIDATE=OUT/'main-candidate'
CANDIDATE.mkdir()
LOGS=OUT/'logs';LOGS.mkdir()
remote={}
try:
    p=subprocess.run(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT,capture_output=True,timeout=35)
    match=re.fullmatch(rb'([0-9a-f]{40})\s+refs/heads/main\s*',p.stdout)
    remote={'exit':p.returncode,'main_sha':match[1].decode() if match else None,
            'diagnostic_sha256':hashlib.sha256(p.stderr).hexdigest() if p.stderr else None}
except subprocess.TimeoutExpired:remote={'exit':'timeout','main_sha':None}
remote['matches_local_main']=remote.get('main_sha')==BASE

tracked=git('ls-tree','-r','--name-only',SOURCE).decode().splitlines()
available=set(tracked)
blob_cache={}
def blob(name):
    if name not in blob_cache:blob_cache[name]=git('show',f'{SOURCE}:{name}')
    return blob_cache[name]
modules=[
 'test_bh07_bank_heap_coverage','test_bh07_bank_console_redaction','test_bh07_bank_owner_graph',
 'test_bh07_bank_navigation_cleanup','test_bh07_owned_browser_cleanup',
 'test_bh07_app_heap_oracle','test_bh07_app_heap_paths','test_bh07_app_heap_evidence',
 'test_bh07_app_heap_build_guard','test_bh07_app_heap_fixture_ownership',
 'test_bh07_app_heap_review_controls','test_bh07_finance_heap_coverage',
]
selected=set()
reasons={}
excluded_paths={'scripts/bh07_appheap/audit_retention_attribution.py'}
output_only_prefixes=('docs/reviews/bh07/browser_evidence','docs/reviews/bh07/bank_receiver_heap_evidence',
                      'docs/reviews/bh07/retention_attribution_evidence')
def add(name,reason):
    if name in excluded_paths or any(name==p or name.startswith(p+'/') for p in output_only_prefixes):return
    if name=='docs/reviews/bh07/review_4184faf_evidence':
        for file in ('redaction_probe.js','publication_probe.js'):add(name+'/'+file,reason)
        return
    if name in available:matches=[name]
    elif name.startswith('scripts/'):return  # module search directory, not an input file
    else:matches=[p for p in tracked if p.startswith(name.rstrip('/')+'/')]
    for p in matches:
        if p in excluded_paths:continue
        if not p.startswith(('scripts/','tests/','docs/reviews/bh07/')):continue
        selected.add(p);reasons.setdefault(p,set()).add(reason)
for name in modules:add(f'tests/{name}.py','selected offline regression suite')
for prefix in ('scripts/bh07_appheap/heap_oracle.py','scripts/bh07_appheap/verify_evidence.py',
               'scripts/bh07_appheap/run_app_profile_heap.js','scripts/bh07_appheap/build_guard.js',
               'scripts/bh07_appheap/disposable_bank_fixture.js','scripts/bh07_appheap/owned_browser_cleanup.js',
               'scripts/bh07_appheap/fixture_controls.js','scripts/bh07_appheap/test_disposable_fixture_scenarios.js',
               'scripts/bh07_browser/run_browser_verification.js',
               'scripts/bh07_browser/assertions.js','scripts/bh07_browser/seed_setup.js',
               'scripts/bh07_browser/clean_and_manifest.py','scripts/bh07_http/seed.sql',
               'docs/reviews/bh07/finance_heap_evidence','docs/reviews/bh07/review_runtime_b13e468_evidence',
               'docs/reviews/bh07/bank_receiver_heap_r4_runtime_evidence'):
    add(prefix,'tooling dependency or provenance fixture')
if 'tests/__init__.py' in available:add('tests/__init__.py','Python package marker')
def root_path(node):
    if isinstance(node,ast.Name) and node.id in ('ROOT','root'):return ''
    if isinstance(node,ast.Constant) and isinstance(node.value,str):return node.value
    if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div):
        left,right=root_path(node.left),root_path(node.right)
        if left is not None and right is not None:return '/'.join(x.strip('/') for x in (left,right) if x)
    return None
scanned=set()
app_reads=set()
while selected-scanned:
    name=sorted(selected-scanned)[0];scanned.add(name)
    if not name.endswith(('.py','.js','.cjs')):continue
    text=blob(name).decode('utf-8-sig')
    references=set(re.findall(r"['\"]((?:docs/reviews/bh07|scripts|lib)/[^'\"\n]+)['\"]",text))
    if name.endswith('.py'):
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div):
                value=root_path(node)
                if value and value.startswith(('docs/reviews/bh07/','scripts/','lib/')):
                    references.add(value)
                    if value.startswith('lib/') and value in available:app_reads.add(value)
    for ref in references:
        if ref.startswith('lib/'):
            continue
        if any(x in ref for x in ('*','{','}')):continue
        add(ref,f'referenced by {name}')
    for relative in re.findall(r"require\(['\"](\.[^'\"]+)['\"]\)",text):
        target=(Path(name).parent/relative).as_posix()
        parts=[]
        for part in target.split('/'):
            if part=='..':parts.pop()
            elif part not in ('','.'):parts.append(part)
        target='/'.join(parts)
        for suffix in ('','.js','.py'):
            if target+suffix in available:add(target+suffix,f'local import from {name}');break

archive=git('archive','--format=zip',BASE)
(OUT/'main-base.zip').write_bytes(archive)
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    for info in z.infolist():
        destination=(CANDIDATE/info.filename).resolve()
        if CANDIDATE.resolve() not in destination.parents and destination!=CANDIDATE.resolve():raise RuntimeError('unsafe archive path')
        if stat.S_ISLNK(info.external_attr>>16):raise RuntimeError('archive symlink requires separate review')
    z.extractall(CANDIDATE)
baseline={p.relative_to(CANDIDATE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
          for p in CANDIDATE.rglob('*') if p.is_file()}
notice_path='docs/reviews/bh07/BANK_TOOLING_INTEGRATION_NOTICE.md'
notice=(f'# Draft bank-tooling integration candidate\n\nBase main: `{BASE}`. Source: `{SOURCE}`.\n\n'
        'This package adds verification tooling and offline regression fixtures only. It does not add BH-07 app/UI or database migrations. '
        'Historical fixture replay and an offline green suite are not a bank runtime run against main. '
        'The accepted runtime remains tied to a095a45. Live runner use requires the BH-07 finance/history UI, RPC/schema and local test fixtures. '
        'No live DB/browser operation was authorized or run for this candidate. Full V2b/BH-07 acceptance and residual-risk approval remain outstanding.\n\n'
        'Scoped Git attributes preserve fixture bytes and LF source on Windows without changing global Git settings. '
        'Status: DRAFT; owner must choose integration scope before merge. Do not merge the full inherited feature branch based on this package.\n')
notice_root=OUT/'notice-source'
(notice_root/notice_path).parent.mkdir(parents=True)
(notice_root/notice_path).write_text(notice,encoding='utf-8',newline='\n')
extra=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null',notice_path],cwd=notice_root,capture_output=True)
if extra.returncode not in (0,1):raise RuntimeError('notice patch generation failed')
fixture_dirs={str(Path(p).parent).replace('\\','/') for p in selected if p.endswith('/hashes.sha256')}
attribute_paths=sorted(selected|{notice_path,'.gitattributes'})
attributes='# Exact integration-package paths only; preserve audited payload bytes.\n'
for p in attribute_paths:
    raw=any(p.startswith(folder+'/') for folder in fixture_dirs)
    attributes+=f'/{p} '+('-text' if raw else 'text eol=lf')+'\n'
(notice_root/'.gitattributes').write_text(attributes,encoding='utf-8',newline='\n')
attribute_patch=subprocess.run(['git','diff','--no-index','--binary','--','/dev/null','.gitattributes'],cwd=notice_root,capture_output=True)
if attribute_patch.returncode not in (0,1):raise RuntimeError('attribute patch generation failed')
patch=attribute_patch.stdout+git('diff','--binary',BASE,SOURCE,'--',*sorted(selected))+extra.stdout
patch_path=OUT/'tooling-only.patch';patch_path.write_bytes(patch)
prefix=CANDIDATE.relative_to(ROOT).as_posix()
def operation(name,args,cwd=ROOT,timeout=180):
    try:
        p=subprocess.run(args,cwd=cwd,capture_output=True,encoding='utf-8',errors='replace',timeout=timeout)
        output=p.stdout+p.stderr;code=p.returncode
    except subprocess.TimeoutExpired as e:
        output='Command timed out; no result claimed.\n';code=124
    (LOGS/f'{name}.log').write_text(output,encoding='utf-8',newline='\n')
    return {'exit':code,'command':args,'test_count':re.findall(r'Ran (\d+) tests?',output)[-1:]}
checks={}
checks['apply_check']=operation('apply_check',['git','apply','--check',f'--directory={prefix}',str(patch_path)])
if checks['apply_check']['exit']:raise RuntimeError('patch apply check failed')
checks['apply']=operation('apply',['git','apply',f'--directory={prefix}',str(patch_path)])
if checks['apply']['exit']:raise RuntimeError('patch apply failed')
(CANDIDATE/'build').mkdir(exist_ok=True)
checks['python']=operation('python',['python','-X','utf8','-m','unittest',*[f'tests.{name}' for name in modules]],CANDIDATE,240)
checks['fixture']=operation('fixture',['node','scripts/bh07_appheap/fixture_controls.js'],CANDIDATE)
for name,folder in [('finance','finance_heap_evidence'),('legacy','review_runtime_b13e468_evidence'),('bank_history','bank_receiver_heap_r4_runtime_evidence')]:
    checks[name]=operation(name,['python','scripts/bh07_appheap/verify_evidence.py','--dir',f'docs/reviews/bh07/{folder}'],CANDIDATE)
checks['pub_offline']=operation('pub_offline',['cmd','/d','/c','flutter pub get --offline'],CANDIDATE)
if checks['pub_offline']['exit']==0:
    checks['flutter_analyze']=operation('flutter_analyze',['cmd','/d','/c','flutter analyze --no-pub'],CANDIDATE)
    checks['flutter_test']=operation('flutter_test',['cmd','/d','/c','flutter test --no-pub'],CANDIDATE)
changed_baseline=[p for p,h in baseline.items() if not (CANDIDATE/p).is_file() or hashlib.sha256((CANDIDATE/p).read_bytes()).hexdigest()!=h]
manifest=[{'path':name,'sha256':hashlib.sha256(blob(name)).hexdigest(),'reason':sorted(reasons[name]),
           'in_main_baseline':name in baseline} for name in sorted(selected)]
manifest.append({'path':notice_path,'sha256':hashlib.sha256(notice.encode()).hexdigest(),'reason':['generated scope notice'],'in_main_baseline':False})
manifest.append({'path':'.gitattributes','sha256':hashlib.sha256(attributes.encode()).hexdigest(),'reason':['generated exact-path line-ending policy'],'in_main_baseline':False})
copied_exact=all(hashlib.sha256((CANDIDATE/m['path']).read_bytes()).hexdigest()==m['sha256'] for m in manifest)
app_scope=all(not m['path'].startswith(('lib/','supabase/','test/','web/')) for m in manifest)
results={'source_sha':SOURCE,'main_sha':BASE,'remote_main':remote,'package':OUT.relative_to(ROOT).as_posix(),
         'selected_file_count':len(manifest),'selected_bytes':sum((CANDIDATE/m['path']).stat().st_size for m in manifest),
         'patch_sha256':hashlib.sha256(patch).hexdigest(),'patch_bytes':len(patch),'checks':checks,
         'baseline_file_count':len(baseline),'changed_baseline_files':changed_baseline,
         'candidate_copy_hashes_match':copied_exact,'no_app_backend_test_web_files_in_patch':app_scope,
         'active_refs_unchanged':git('rev-parse','HEAD').decode().strip()==SOURCE and git('rev-parse','main').decode().strip()==BASE,
         'static_direct_app_contract_paths':sorted(app_reads),
         'excluded_non_input_paths':[ *sorted(excluded_paths),*output_only_prefixes],
         'live_bank_runtime':'NOT RUN — main lacks BH-07 app/backend prerequisites',
         'merge_status':'DRAFT — no merge authorization or whole-BH07 acceptance'}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
(OUT/'results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(results,indent=2))
if any(c['exit'] for c in checks.values()) or changed_baseline or not copied_exact or not app_scope:raise SystemExit(1)
