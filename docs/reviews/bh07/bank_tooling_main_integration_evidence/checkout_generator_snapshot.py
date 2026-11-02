import hashlib
import json
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
label=sys.argv[1] if len(sys.argv)>1 else 'v4'
package=root/'build'/f'bh07-main-integration-62d2c67-57cd2c4-{label}'
data=json.loads((package/'results.json').read_bytes())
manifest=json.loads((package/'manifest.json').read_bytes())
repo=package/'git-checkout-smoke'
fresh=package/'index-checkout'
if repo.exists() or fresh.exists():raise SystemExit('fresh-checkout output already exists')
logs=package/'logs'
def run(name,args,cwd=root,timeout=180):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    (logs/f'{name}.log').write_text(p.stdout+p.stderr,encoding='utf-8',newline='\n')
    return p
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
main=subprocess.check_output(['git','rev-parse','main'],cwd=root,text=True).strip()
clone=run('checkout_clone',['git','clone','--shared','--no-checkout','--no-hardlinks',str(root),str(repo)])
assert clone.returncode==0
checkout=run('checkout_base',['git','checkout','--detach',data['main_sha']],repo)
assert checkout.returncode==0
baseline_names=subprocess.check_output(['git','ls-tree','-r','--name-only',data['main_sha']],cwd=repo,text=True).splitlines()
baseline_before={name:hashlib.sha256((repo/name).read_bytes()).hexdigest() for name in baseline_names}
apply=run('checkout_apply_index',['git','apply','--cached',str(package/'tooling-only.patch')],repo)
assert apply.returncode==0
refresh=run('checkout_worktree_refresh',['git','checkout-index','--all','--force'],repo)
assert refresh.returncode==0
staged=subprocess.check_output(['git','diff','--cached','--name-only','-z'],cwd=repo).decode().split('\0')
staged={p for p in staged if p}
assert staged=={m['path'] for m in manifest}
fresh.mkdir()
prefix=fresh.as_posix()+'/'
export=run('checkout_index_export',['git','checkout-index','--all',f'--prefix={prefix}'],repo)
assert export.returncode==0
mismatch=[m['path'] for m in manifest if hashlib.sha256((fresh/m['path']).read_bytes()).hexdigest()!=m['sha256']]
worktree_mismatch=[m['path'] for m in manifest if hashlib.sha256((repo/m['path']).read_bytes()).hexdigest()!=m['sha256']]
baseline_changed=[name for name,digest in baseline_before.items() if hashlib.sha256((repo/name).read_bytes()).hexdigest()!=digest]
(repo/'build').mkdir(exist_ok=True)
modules=data['checks']['python']['command']
unit=run('checkout_python',modules,repo,240)
audits={}
for name,folder in [('finance','finance_heap_evidence'),('legacy','review_runtime_b13e468_evidence'),('bank_history','bank_receiver_heap_r4_runtime_evidence')]:
    audits[name]=run('checkout_'+name,['python','scripts/bh07_appheap/verify_evidence.py','--dir',f'docs/reviews/bh07/{folder}'],repo).returncode
fixture=run('checkout_fixture',['node','scripts/bh07_appheap/fixture_controls.js'],repo)
counts=[]
import re
counts=re.findall(r'Ran (\d+) tests?',unit.stdout+unit.stderr)
config=subprocess.run(['git','config','--get','core.autocrlf'],cwd=repo,capture_output=True,text=True)
result={'base_sha':data['main_sha'],'staged_additions':len(staged),
        'ignored_fixture_logs_staged':sum(p.endswith('.log') for p in staged),
        'fresh_checkout_byte_mismatches':mismatch,'python_exit':unit.returncode,'python_tests':int(counts[-1]) if counts else None,
        'working_tree_byte_mismatches':worktree_mismatch,'original_clone_files_changed':baseline_changed,
        'setup_build_directory':True,'apply_mode':'git apply --cached then checkout-index --all --force in a fresh clean clone',
        'clone_core_autocrlf':config.stdout.strip() or 'unset',
        'historical_auditor_exits':audits,'fixture_exit':fixture.returncode,
        'original_head_unchanged':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==head,
        'original_main_unchanged':subprocess.check_output(['git','rev-parse','main'],cwd=root,text=True).strip()==main}
(package/'checkout_smoke.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(result,indent=2))
raise SystemExit(bool(mismatch) or bool(worktree_mismatch) or bool(baseline_changed) or unit.returncode or any(audits.values()) or fixture.returncode or not result['original_head_unchanged'] or not result['original_main_unchanged'])
