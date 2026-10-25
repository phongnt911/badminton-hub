"""Isolated reviewer controls; no implementation or author evidence files are changed."""
import contextlib,hashlib,importlib.util,io,json,shutil,subprocess,tempfile
from pathlib import Path
ROOT=Path.cwd();out={}
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=load('heap_audit',ROOT/'scripts/bh07_heap/audit_ast_memory.py')
v=load('heap_verify',ROOT/'scripts/bh07_heap/clean_and_manifest.py')
r=load('heap_runner',ROOT/'scripts/bh07_heap/run_heap_verification.py')
with tempfile.TemporaryDirectory(prefix='v2b-review-') as d:
 d=Path(d)
 # Execute the exact audit CLI on a disposable copy with all 38 lib files.
 copy=d/'audit_copy';(copy/'scripts/bh07_heap').mkdir(parents=True);shutil.copy2(ROOT/'scripts/bh07_heap/audit_ast_memory.py',copy/'scripts/bh07_heap/audit_ast_memory.py');shutil.copytree(ROOT/'lib',copy/'lib')
 p=subprocess.run(['python',str(copy/'scripts/bh07_heap/audit_ast_memory.py')],capture_output=True,text=True)
 authored=ROOT/'docs/reviews/bh07/private_heap_evidence/ast_memory_audit.json';created=copy/'docs/reviews/bh07/private_heap_evidence/ast_memory_audit.json'
 out['exact_ast_cli']={'exit':p.returncode,'stdout':p.stdout,'report_matches_author':created.read_bytes()==authored.read_bytes()}
 cases={'typed_static_list':'class X {\n static List<Object> leak = <Object>[];\n}', 'inferred_static_constructor':'class X {\n static final leak = List<Object>.empty(growable: true);\n}', 'global_list':'final leak = <Object>[];'}
 out['static_controls']={}
 for name,code in cases.items():
  p=d/name;p.mkdir();(p/'sample.dart').write_text(code);n,issues=a.audit_static_and_globals(p);out['static_controls'][name]={'scanned':n,'issues':len(issues)}
 out['subscription_controls']={}
 for name,code in {'nullable_uncancelled':'class X {\n StreamSubscription<int>? _sub;\n void dispose() {}\n}', 'remove_outside_dispose':'class X {\n void init() { auth.addListener(_onAuthChanged); }\n void unused() { auth.removeListener(_onAuthChanged); }\n void dispose() {}\n}'}.items():
  lib=d/name;(lib/'providers').mkdir(parents=True);(lib/'providers/auth_provider.dart').write_text(code);out['subscription_controls'][name]=a.audit_listeners_and_subscriptions(lib)['auth_provider.dart']
 # Sanitized dummy failure: no source/author bundle mutation.
 target=d/'failed_summary';target.mkdir();r.EVIDENCE_DIR=str(target)
 with contextlib.redirect_stdout(io.StringIO()):r.generate_summary('synthetic-sha',True,{'os':'synthetic'},False,False,'synthetic failed test')
 summary=json.loads((target/'summary.json').read_text());report=(target/'heap_verification_report.md').read_text()
 out['failed_run_summary']={'ast':summary['ast_audit'],'suite_verdict':summary['heap_test_suite']['verdict'],'control_results':summary['heap_test_suite']['controls'],'report_claims_7_of_7_pass':'7/7' in report and 'PASS' in report}
 # --verify controls: only temporary copies of the handed-off bundle.
 source=d/'synthetic_valid_bundle';source.mkdir();(source/'summary.json').write_text('{}\n');(source/'hashes.sha256').write_text(hashlib.sha256((source/'summary.json').read_bytes()).hexdigest()+'  summary.json\n');out['verify_controls']={}
 for case in ['positive','manifest_crlf','hash_mismatch','missing','extra']:
  p=d/('ev_'+case);shutil.copytree(source,p);mf=p/'hashes.sha256'
  if case=='manifest_crlf':mf.write_bytes(mf.read_bytes().replace(b'\n',b'\r\n'))
  if case=='hash_mismatch':(p/'summary.json').write_text('{"changed": true}\n')
  if case=='missing':(p/'summary.json').unlink()
  if case=='extra':(p/'extra.txt').write_text('synthetic extra\n')
  before={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in p.iterdir()}
  q=subprocess.run(['python',str(ROOT/'scripts/bh07_heap/clean_and_manifest.py'),'--verify','--dir',str(p)],capture_output=True,text=True)
  after={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in p.iterdir()}
  out['verify_controls'][case]={'exit':q.returncode,'readonly':before==after}
print(json.dumps(out,indent=2))
