import ast,copy,unittest
from pathlib import Path
tree=ast.parse(Path('.build/lifecycle_fixture.py').read_text())
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_gate')
ns={};exec(compile(ast.Module(body=[node],type_ignores=[]),'gate','exec'),ns)
gate=ns['validate_gate']
def valid(stage):
 n=stage=='completed'
 return dict(players_present=2,revision_count=1,charge_count=2,charge_total=200000,lifecycle='completed' if n else 'in_progress',version=3 if n else 2,completed_audits=int(n),complete_operations=int(n),exact_request_operations=int(n),exact_request_audits=int(n),charges=[100000,100000],payments=0,billing_current=True)
class Gate(unittest.TestCase):
 def test_positive_both_stages(self):
  for stage in ['offline','completed']:gate(valid(stage),stage)
 def test_offline_orphan_operation(self):
  r=valid('offline');r['exact_request_operations']=1
  with self.assertRaises(AssertionError):gate(r,'offline')
 def test_completion_wrong_request(self):
  for k in ['exact_request_operations','exact_request_audits']:
   r=valid('completed');r[k]=0
   with self.subTest(k=k),self.assertRaises(AssertionError):gate(r,'completed')
 def test_unequal_charges(self):
  r=valid('offline');r['charges']=[99999,100001]
  with self.assertRaises(AssertionError):gate(r,'offline')
 def test_unexpected_payment(self):
  r=valid('offline');r['payments']=1
  with self.assertRaises(AssertionError):gate(r,'offline')
 def test_stale_billing(self):
  r=valid('offline');r['billing_current']=False
  with self.assertRaises(AssertionError):gate(r,'offline')
unittest.main()
