"""Frozen, leakage-safe Stage 22 linear/MLP probe and counterfactual analysis."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
ROOT=Path('/root/shared-nvme/openpi-robot-runtime/results/stage22_counterfactual_intent'); DATA=ROOT/'data.json'
DIRECTIONS=np.array(((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)),float); NAMES=('+x','-x','+y','-y','+z','-z')
def metrics(pred,y,groups,conditions):
 norm=np.linalg.norm(pred,axis=1); cosine=np.divide((pred*y).sum(1),norm,out=np.zeros(len(y)),where=norm>1e-12)
 cls=(pred@DIRECTIONS.T).argmax(1); truth=(y@DIRECTIONS.T).argmax(1); six=float((cls==truth).mean())
 pair=[]
 for group in sorted(set(groups)):
  for a,b in ((0,1),(2,3),(4,5)):
   ia=np.where((groups==group)&(truth==a))[0]; ib=np.where((groups==group)&(truth==b))[0]
   if len(ia) and len(ib): pair.append(bool((pred[ia]@DIRECTIONS[a]).mean()>0 and (pred[ib]@DIRECTIONS[b]).mean()>0))
 return {'mse':float(((pred-y)**2).mean()),'cosine':float(cosine.mean()),'six_way_accuracy':six,'pairwise_opposite_discrimination':float(np.mean(pair))}
def fit(kind,Xtr,Ytr,Xte,seed):
 mean=Xtr.mean(0); std=Xtr.std(0); std[std<1e-12]=1.; a=(Xtr-mean)/std; b=(Xte-mean)/std
 if kind=='linear':
  return b@np.linalg.solve(a.T@a+1e-3*np.eye(a.shape[1]),a.T@Ytr)
 # Fixed small ReLU MLP, full-batch Adam: no external ML package/dependency.
 rng=np.random.default_rng(seed); width=32; w1=rng.normal(0,.08,(a.shape[1],width)); b1=np.zeros(width); w2=rng.normal(0,.08,(width,3)); b2=np.zeros(3)
 m=[np.zeros_like(x) for x in (w1,b1,w2,b2)]; v=[np.zeros_like(x) for x in (w1,b1,w2,b2)]
 for step in range(1,801):
  h0=a@w1+b1; h=np.maximum(h0,0); pred=h@w2+b2; grad=2*(pred-Ytr)/len(a); grads=(a.T@((grad@w2.T)*(h0>0)),((grad@w2.T)*(h0>0)).sum(0),h.T@grad,grad.sum(0))
  for i,(param,g) in enumerate(zip((w1,b1,w2,b2),grads)):
   m[i]=.9*m[i]+.1*g; v[i]=.999*v[i]+.001*g*g; param-=.01*(m[i]/(1-.9**step))/(np.sqrt(v[i]/(1-.999**step))+1e-8)
 return np.maximum(b@w1+b1,0)@w2+b2
def summarize(items):
 keys=('mse','cosine','six_way_accuracy','pairwise_opposite_discrimination'); return {k:{'mean':float(np.mean([x[k] for x in items])),'std':float(np.std([x[k] for x in items],ddof=0))} for k in keys}
def main():
 raw=json.loads(DATA.read_text())['rows']; rows=[r for r in raw if r['safe_hold'] is None]
 assert len(rows)==480 and {r['group_id'] for r in rows}==set(range(20))
 state=np.array([list(r['joint_position'])+[r['gripper_position']] for r in rows],float); action=np.array([r['action_feature'] for r in rows],float); y=np.array([r['teacher_cartesian_unit_direction'] for r in rows],float); groups=np.array([r['group_id'] for r in rows]); cond=np.array([NAMES.index(r['condition']) for r in rows]); train=np.array([r['split']=='train' for r in rows]); test=np.array([r['split']=='test' for r in rows])
 # Integrity: all 24 rows/group share state; each condition appears four times.
 integrity={'rows':len(rows),'safe_holds':len(raw)-len(rows),'groups':len(set(groups)),'max_within_group_state_delta':max(float(abs(state[groups==g]-state[groups==g][0]).max()) for g in set(groups)),'condition_counts':{n:int((cond==i).sum()) for i,n in enumerate(NAMES)},'split_counts':{s:sum(r['split']==s for r in rows) for s in ('train','validation','test')}}
 results={}; feature_sets={'state_only':state,'pi05_only':action,'state_plus_real_pi05':np.c_[state,action]}
 for kind in ('linear','mlp'):
  block={}
  for name,X in feature_sets.items():
   vals=[metrics(fit(kind,X[train],y[train],X[test],seed),y[test],groups[test],cond[test]) for seed in (11,22,33)]
   block[name]={'seeds':[11,22,33],'runs':vals,'mean_std':summarize(vals)}
  shuffled=[]
  for shuffle_seed in (101,202,303):
   rng=np.random.default_rng(shuffle_seed); perm=rng.permutation(train.sum()); X=np.c_[state,action]; Xtr=X[train].copy(); Xtr[:,state.shape[1]:]=Xtr[perm,state.shape[1]:]
   vals=[metrics(fit(kind,Xtr,y[train],X[test],seed),y[test],groups[test],cond[test]) for seed in (11,22,33)]
   shuffled.append({'shuffle_seed':shuffle_seed,'runs':vals,'mean_std':summarize(vals)})
  flat=[run for entry in shuffled for run in entry['runs']]; block['state_plus_shuffled_pi05']={'shuffle_seeds':[101,202,303],'initialization_seeds':[11,22,33],'by_shuffle':shuffled,'mean_std_all_9':summarize(flat)}
  # Constant +X is selected before test and labels are balanced.
  constant=np.tile(DIRECTIONS[0],(test.sum(),1)); block['constant_plus_x']=metrics(constant,y[test],groups[test],cond[test])
  real=block['state_plus_real_pi05']['mean_std']; shuf=block['state_plus_shuffled_pi05']['mean_std_all_9']; state_m=block['state_only']['mean_std']
  block['real_minus_state']={k:real[k]['mean']-state_m[k]['mean'] for k in real}; block['real_minus_shuffled']={k:real[k]['mean']-shuf[k]['mean'] for k in real}; results[kind]=block
 gate=[]
 for kind,b in results.items():
  a=b['real_minus_state']; c=b['real_minus_shuffled']; gate.append(a['six_way_accuracy']>=.10 and a['pairwise_opposite_discrimination']>=.10 and a['cosine']>=.05 and c['six_way_accuracy']>=.10 and c['pairwise_opposite_discrimination']>=.10 and c['cosine']>=.05)
 report={'scope':'Stage 22 frozen feature-only probes; no target coordinates, IDs, prompt tokens or pixels are probe inputs','integrity':integrity,'results':results,'gate_rule':'all model families must improve state-only and shuffled by >=0.10 six-way/pairwise and >=0.05 cosine','gate_passed':all(gate),'sequence_adapter':'permitted only if gate_passed else blocked'}
 (ROOT/'probe_report.json').write_text(json.dumps(report,indent=2)); print(json.dumps({'integrity':integrity,'gate_passed':report['gate_passed'],'sequence_adapter':report['sequence_adapter']},indent=2))
if __name__=='__main__': main()
