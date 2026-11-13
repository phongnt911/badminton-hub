from pathlib import Path
import json,sys,hashlib,re
sys.path.insert(0,str(Path.cwd()))
from scripts.bh07_appheap import heap_oracle as h
raw=Path(sys.argv[1]).read_bytes()
doc,error,details=h.parse_snapshot(raw)
assert not error,error
layout,error=h._layout(doc);assert not error,error
parent,_,error=h._root_reach(doc,layout);assert not error,error
n,e,strings=doc['nodes'],doc['edges'],doc['strings']
w,ew=layout['node_width'],layout['edge_width']
nt,et=layout['node_type_names'],layout['edge_type_names']
def node(i):
 return nt[n[i*w+layout['type_i']]],strings[n[i*w+layout['name_i']]]
targets={name:[] for name in ['AuthProvider','SessionProvider','ClubProvider','FinanceProvider']}
offset=0;offsets=[]
for i in range(doc['snapshot']['node_count']):
 offsets.append(offset);offset+=n[i*w+layout['count_i']]
 t,name=node(i)
 if t=='object' and name in targets:targets[name].append(i)
def edges(i):
 for r in range(offsets[i],offsets[i]+n[i*w+layout['count_i']]):
  b=r*ew;kind=et[e[b+layout['etype_i']]];label=e[b+layout['ename_i']]
  if kind not in ['element','hidden']:label=strings[label]
  yield kind,label,e[b+layout['to_i']]//w
def safe_target(i):
 t,name=node(i)
 return {'node_type':t,'class_name':name if name in targets or name in ['BoundClosure','Closure','Array','_GrowableList','_InheritedProviderScopeElement'] or ('Provider' in name and 'onAuthChanged' in name) else None}
result={'scope':'guest_baseline_layout_calibration_only','full_listener_gate':'NOT_RUN','snapshot_bytes':len(raw),'snapshot_sha256':hashlib.sha256(raw).hexdigest(),'node_count':doc['snapshot']['node_count'],'node_fields':doc['snapshot']['meta']['node_fields'],'edge_fields':doc['snapshot']['meta']['edge_fields'],'rooted_auth_heap_object_ids':[str(n[i*w+doc['snapshot']['meta']['node_fields'].index('id')]) for i in targets['AuthProvider'] if parent[i]>=0],'providers':{}}
for name,ids in targets.items():
 records=[]
 for i in ids:
  if parent[i]<0:continue
  properties={};listeners=[]
  for kind,label,to in edges(i):
   if kind=='property' and (label.startswith('ChangeNotifier__') or label in ['auth','_currentUser','_isLoading','_isSubmitting','_instructions','_finance','_ledger','_sessionSummary','_summary']):
    properties[label]=safe_target(to)
    # Only fixed structural literals/counters, never arbitrary string contents.
    tn,nn=node(to)
    literals={'null','undefined','true','false'}
    literal=nn if nn in literals else None
    for kk,ll,zz in edges(to):
     if kk=='internal' and ll=='to_string' and node(zz)[1] in literals:literal=node(zz)[1]
    properties[label]['primitive_literal']=literal
    if tn=='number':properties[label]['numeric_name']=nn if re.fullmatch(r'-?\d+(?:\.\d+)?',nn) else 'not_decoded'
    if label=='ChangeNotifier__listeners':
     # Enumerate array/backing elements only; never prototype/global graph closure.
     todo=[(to,0)];seen=set()
     while todo:
      j,depth=todo.pop()
      if j in seen:continue
      seen.add(j)
      assert len(seen)<=1000,'listener calibration budget exceeded'
      for k,l,z in edges(j):
       if k=='element':
        rec=safe_target(z);rec['slot']=l
        rec['bound_receiver']=[safe_target(v) for a,b,v in edges(z) if a=='property' and b=='_receiver']
        methods=[];proto_debug=[];chain=[(z,0)];visited=set()
        while chain:
         q,level=chain.pop()
         if q in visited:continue
         visited.add(q)
         for aa,bb,vv in edges(q):
          if aa=='property' and bb in ['$_name','__proto__']:proto_debug.append({'level':level,'key':bb,'target_type':node(vv)[0],'target_name':node(vv)[1] if node(vv)[1] in ['BoundClosure','Object','tear_off','_onAuthChanged$0','markNeedsNotifyDependents$0','_session_provider$_onAuthChanged$0'] else '<unrecognized>'})
          if aa=='property' and bb=='$_name' and node(vv)[0]=='string' and node(vv)[1] in ['_club_provider$_onAuthChanged$0','_session_provider$_onAuthChanged$0','_onAuthChanged$0','markNeedsNotifyDependents$0']:methods.append(node(vv)[1])
          if level<4 and aa=='property' and bb=='__proto__':chain.append((vv,level+1))
        rec['recognized_tearoff_methods']=sorted(set(methods));rec['prototype_debug']=proto_debug
        listeners.append(rec)
       elif depth<2 and k=='internal' and l=='elements':todo.append((z,depth+1))
  records.append({'strong_root_reachable':True,'selected_properties':properties,'listener_slot_descriptors':listeners})
 result['providers'][name]={'all_object_nodes':len(ids),'strong_root_reachable_count':len(records),'records':records}
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'scan':'complete','scope':result['scope'],'counts':{k:v['strong_root_reachable_count'] for k,v in result['providers'].items()}}))
