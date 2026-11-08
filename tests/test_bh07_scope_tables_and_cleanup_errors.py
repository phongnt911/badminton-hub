"""Regression controls for installed V8 scope tables and finally cleanup failures."""
import copy
import json
import subprocess
import unittest
from tests.test_bh07_app_heap_oracle import snapshot_body, scan_body


def scope_snapshot():
    doc = json.loads(snapshot_body(['scope-variable']))
    strings = doc.pop('strings')
    doc['snapshot']['meta'].update({
        'scope_fields': ['script_node_index', 'scope_id', 'depth', 'scope_context_vars_count', 'scope_uses_count'],
        'scope_context_var_fields': ['name'],
        'scope_use_fields': ['declaring_scope_id', 'slot_index'],
    })
    doc.update(scopes=[0, -1, 0, 1, 1], scope_context_vars=[0], scope_uses=[-1, 0], strings=strings)
    return doc


class ScopeTables(unittest.TestCase):
    def test_current_v8_tables_and_legacy_both_parse(self):
        self.assertTrue(scan_body(snapshot_body(['scope-variable']))['ok'])
        result = scan_body(json.dumps(scope_snapshot()))
        self.assertTrue(result['ok'], result.get('error'))

    def test_malformed_scope_tables_fail_closed(self):
        base = scope_snapshot()
        mutations = [
            lambda d: d.pop('scope_uses'),
            lambda d: d.update(scopes={}),
            lambda d: d.update(scopes=[0, -1, 0, 1]),
            lambda d: d['scopes'].__setitem__(0, 1),
            lambda d: d['scopes'].__setitem__(2, -1),
            lambda d: d['scopes'].__setitem__(3, 2),
            lambda d: d['scopes'].__setitem__(4, 2),
            lambda d: d.update(scope_context_vars=[True]),
            lambda d: d.update(scope_context_vars=[999999]),
            lambda d: d.update(scope_uses=[-1]),
            lambda d: d['snapshot']['meta'].update(scope_fields=['wrong']),
        ]
        for mutate in mutations:
            doc = copy.deepcopy(base)
            mutate(doc)
            with self.subTest(mutation=mutations.index(mutate)):
                self.assertFalse(scan_body(json.dumps(doc))['ok'])


class FinallyCleanup(unittest.TestCase):
    def test_real_finally_metadata_continues_after_eacces(self):
        script = r"""
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync('scripts/bh07_appheap/run_app_profile_heap.js','utf8');
const start=source.indexOf('    const chromeDir = path.join(os.tmpdir()');
const end=source.indexOf('    // The run-only expense row',start);
const helperStart=source.indexOf('function evaluateCleanupState(');
const helperEnd=source.indexOf('\nfunction renderReport(',helperStart);
if(start<0||end<0||helperStart<0||helperEnd<0)throw Error('test boundary missing');
const inaccessible=()=>{const error=Error('synthetic');error.code='EACCES';throw error;};
const context={fs:{existsSync:()=>true,rmSync:inaccessible,readdirSync:inaccessible},
 path,os:{tmpdir:()=>'/tmp'},process:{pid:123},ROOT:'/repo',DUMPS:'/tmp/owned',
 browserCleanupOk:true,summary:{cleanup:{}},fixtureCleanupOk:()=>false,continued:false};
vm.runInNewContext(source.slice(helperStart,helperEnd)+'\n'+source.slice(start,end)+'\ncontinued=true;',context);
console.log(JSON.stringify({continued:context.continued,cleanup:context.summary.cleanup}));
"""
        run = subprocess.run(['node', '-e', script], capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)
        result = json.loads(run.stdout)
        self.assertTrue(result['continued'])
        self.assertIsNone(result['cleanup']['raw_snapshots_remaining'])
        self.assertFalse(result['cleanup']['dumps_dir_removed'])


if __name__ == '__main__':
    unittest.main()
