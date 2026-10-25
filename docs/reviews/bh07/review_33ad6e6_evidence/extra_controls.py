"""Reviewer controls on temp fixtures only; implementation/evidence remain unchanged."""
import contextlib,importlib.util,io,json,subprocess,tempfile
from pathlib import Path
ROOT=Path.cwd();out={}
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=load('audit',ROOT/'scripts/bh07_heap/audit_ast_memory.py');r=load('runner',ROOT/'scripts/bh07_heap/run_heap_verification.py')
with tempfile.TemporaryDirectory(prefix='v2b-extra-') as d:
 d=Path(d);out['dispose_controls']={}
 cases={
 'real_cancel_positive':"class X {\n StreamSubscription<int>? _sub;\n void dispose() { _sub?.cancel(); }\n}",
 'comment_cancel':"class X {\n StreamSubscription<int>? _sub;\n void dispose() {\n // _sub?.cancel();\n }\n}",
 'string_cancel':"class X {\n StreamSubscription<int>? _sub;\n void dispose() { print('_sub?.cancel()'); }\n}",
 'comment_remove':"class X {\n void init() { auth.addListener(_onAuthChanged); }\n void dispose() { /* auth.removeListener(_onAuthChanged); */ }\n}"}
 for name,code in cases.items():
  p=d/name;(p/'providers').mkdir(parents=True);(p/'providers/auth_provider.dart').write_text(code);out['dispose_controls'][name]=a.audit_listeners_and_subscriptions(p)['auth_provider.dart']
 p=d/'static_comment';p.mkdir();(p/'sample.dart').write_text('class X {\n static final leak = <Object>[]; // static const\n}')
 n,issues=a.audit_static_and_globals(p);out['mutable_static_with_comment']={'scanned':n,'issues':len(issues)}
 out['summary_controls']={}
 for name,ok,text in [('full_positive',True,'00:00 +7: All tests passed!'),('subset_only',True,'00:00 +1: All tests passed!'),('no_tests',True,'No tests ran.'),('failed_test',False,'00:00 +0 -1: Some tests failed.')]:
  p=d/name;p.mkdir();r.EVIDENCE_DIR=str(p);(p/'ast_memory_audit.json').write_text(json.dumps({'overall_ast_verdict':'CLEAN','static_mutable_collections_found':0,'providers_lifecycle_audit':{'auth_provider.dart':{'leak_risk':'NONE'}}}))
  with contextlib.redirect_stdout(io.StringIO()):r.generate_summary('synthetic',False,{'os':'synthetic'},True,ok,text)
  s=json.loads((p/'summary.json').read_text());rep=(p/'heap_verification_report.md').read_text()
  out['summary_controls'][name]={'suite':s['heap_test_suite'],'markdown_claims_7_of_7': '7/7 Provider test PASS' in rep}
 # Git status failure must not be turned into a proven clean checkout.
 original=r.subprocess.check_output
 def fake_git(args,**kw):
  if args[:3]==['git','rev-parse','HEAD']:return '33ad6e6fd7e33b8495ec9dda0732df1b6df2096b\n'
  raise subprocess.CalledProcessError(128,args)
 r.subprocess.check_output=fake_git
 try:
  sha,dirty,paths,hashes=r.get_git_info();out['git_status_failure']={'sha':sha,'git_dirty':dirty,'dirty_paths':paths}
 finally:r.subprocess.check_output=original
p=subprocess.run(['git','cat-file','-e','2dac37434df6b9409b53e36e65f3bc85bf755b40^{commit}'],capture_output=True,text=True)
out['base_provenance']={'requested_base_resolves':p.returncode==0,'actual_base':subprocess.check_output(['git','rev-parse','33ad6e6^'],text=True).strip()}
print(json.dumps(out,indent=2))
