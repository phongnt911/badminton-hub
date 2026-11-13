import ast,copy,unittest
from pathlib import Path
tree=ast.parse(Path('.build/payment_fixture.py').read_text())
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_gate')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'gate','exec'),ns);gate=ns['validate_gate']
def valid(confirmed):
 n=int(confirmed)
 return dict(payment_count=1,amount=100000,method='bank_transfer',status='confirmed' if confirmed else 'submitted',submitted_by_guest=True,confirmed_by_owner=confirmed,confirmed_by_is_null=not confirmed,confirmed_at_is_null=not confirmed,submit_ops=1,submit_audits=1,all_submit_audits=1,ledger_count=n,confirm_ops=n,confirm_audits=n,all_confirm_audits=n,ledger_total=100000 if confirmed else 0,ledger_valid=True,total_paid=100000 if confirmed else 0,outstanding=0 if confirmed else 100000,charges=[100000,100000],billing_current=True)
class Gate(unittest.TestCase):
 def test_positive_boundaries(self):
  gate(valid(False),False);gate(valid(True),True)
 def test_submitted_not_paid_or_ledger(self):
  for k,v in [('total_paid',100000),('outstanding',0),('ledger_count',1),('ledger_total',100000)]:
   r=valid(False);r[k]=v
   with self.subTest(field=k),self.assertRaises(AssertionError):gate(r,False)
 def test_duplicate_or_missing_records(self):
  for k,v in [('payment_count',2),('ledger_count',2),('confirm_ops',2),('submit_audits',0),('all_submit_audits',2),('all_confirm_audits',2),('confirm_audits',0)]:
   r=valid(True);r[k]=v
   with self.subTest(field=k),self.assertRaises(AssertionError):gate(r,True)
 def test_wrong_actor_or_ledger_target(self):
  for k in ['submitted_by_guest','confirmed_by_owner','ledger_valid']:
   r=valid(True);r[k]=False
   with self.subTest(field=k),self.assertRaises(AssertionError):gate(r,True)
 def test_wrong_amount_status_or_billing(self):
  for k,v in [('amount',99999),('status','submitted'),('method','cash'),('charges',[99999,100001]),('billing_current',False)]:
   r=valid(True);r[k]=v
   with self.subTest(field=k),self.assertRaises(AssertionError):gate(r,True)
 def test_confirmation_metadata(self):
  for confirmed,k,v in [(False,'confirmed_by_is_null',False),(False,'confirmed_at_is_null',False),(True,'confirmed_at_is_null',True)]:
   r=valid(confirmed);r[k]=v
   with self.subTest(confirmed=confirmed,field=k),self.assertRaises(AssertionError):gate(r,confirmed)
unittest.main()
