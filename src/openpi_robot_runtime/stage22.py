"""Deterministic CPU-only counterfactual benchmark construction and audits."""
from __future__ import annotations
import numpy as np
DIRECTIONS={'+x':(1.,0.,0.),'-x':(-1.,0.,0.),'+y':(0.,1.,0.),'-y':(0.,-1.,0.),'+z':(0.,0.,1.),'-z':(0.,0.,-1.)}
def split(group:int)->str:return 'train' if group<12 else 'validation' if group<16 else 'test'
def generate(seed:int=20260822):
 rng=np.random.default_rng(seed); rows=[]
 for group in range(20):
  state=tuple(float(v) for v in rng.uniform(-.3,.3,8))
  for condition,direction in DIRECTIONS.items():rows.append({'group_id':group,'split':split(group),'condition':condition,'state':state,'teacher_direction':direction,'magnitude_m':.10})
 return rows
def audit(rows):
 result={}
 for name in ('train','validation','test'):
  data=[r for r in rows if r['split']==name]; vectors=np.array([r['teacher_direction'] for r in data]); counts={c:sum(r['condition']==c for r in data) for c in DIRECTIONS}; mean=vectors.mean(0); result[name]={'n':len(data),'direction_counts':counts,'constant_cosine_abs':float(np.linalg.norm(mean)),'max_within_group_state_delta':max(float(np.max(np.abs(np.array([r['state'] for r in data if r['group_id']==g])-np.array([r['state'] for r in data if r['group_id']==g])[0]))) for g in set(r['group_id'] for r in data)),'state_only_condition_chance':1/6,'nearest_neighbor_condition_accuracy_upper_bound':1/6}
 return result
