"""CPU-only, leakage-audited frozen Stage 21A linear and MLP probes."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np, torch
DATA=Path('/root/shared-nvme/openpi-robot-runtime/results/stage21a_cartesian_probe/data.json'); OUT=DATA.with_name('probe_report.json')
INIT=(11,22,33); SHUFFLES=(101,202,303)
def metrics(p,y):
 p=p.detach().cpu().numpy();y=y.detach().cpu().numpy(); d=(p*y).sum(1); c=d/np.maximum(np.linalg.norm(p,axis=1)*np.linalg.norm(y,axis=1),1e-9)
 return {'mse':float(((p-y)**2).mean()),'cosine':float(c.mean()),'direction_rate':float((c>0).mean()),'direction_rate_0_5':float((c>.5).mean()),'projected_progress':float(d.mean()),'magnitude_error':float(np.abs(np.linalg.norm(p,axis=1)-np.linalg.norm(y,axis=1)).mean())}
def fit_mlp(x,y,train,val,seed):
 torch.manual_seed(seed);n=torch.nn.Sequential(torch.nn.Linear(x.shape[1],128),torch.nn.ReLU(),torch.nn.Linear(128,128),torch.nn.ReLU(),torch.nn.Linear(128,3));o=torch.optim.AdamW(n.parameters(),lr=1e-3,weight_decay=1e-4);best=(float('inf'),None);bad=0
 for epoch in range(300):
  l=torch.nn.functional.mse_loss(n(x[train]),y[train]);o.zero_grad();l.backward();o.step();v=torch.nn.functional.mse_loss(n(x[val]),y[val]).item()
  if v<best[0]:best=(v,{k:t.detach().clone() for k,t in n.state_dict().items()});bad=0
  else:bad+=1
  if bad>=30:break
 n.load_state_dict(best[1]);return n,epoch+1,best[0]
def fit_linear(x,y,train):
 z=torch.cat((x[train],torch.ones((len(train),1))),1);w=torch.linalg.solve(z.T@z+1e-4*torch.eye(z.shape[1]),z.T@y[train]);return lambda q:torch.cat((q,torch.ones((len(q),1))),1)@w
def main():
 rows=[r for r in json.loads(DATA.read_text())['rows'] if r['safe_hold'] is None];assert len(rows)==1440
 s=np.array([r['joint_position']+[r['gripper_position']] for r in rows],np.float32);a=np.array([r['action_feature'] for r in rows],np.float32);y=torch.tensor(np.array([r['teacher_cartesian_unit_direction'] for r in rows],np.float32));split=np.array([r['split'] for r in rows]);ids=np.array([r['target_id'] for r in rows]);ix={k:np.where(split==k)[0] for k in ('train','validation','test')};out={'rows':len(rows),'split_sizes':{k:len(v) for k,v in ix.items()},'models':[]}
 for cls in ('linear','mlp'):
  for base in ('state','action','real','shuffled'):
   pairs=([(None,None)] if cls=='linear' else [(i,None) for i in INIT]) if base!='shuffled' else ([(None,q) for q in SHUFFLES] if cls=='linear' else [(i,q) for i in INIT for q in SHUFFLES])
   for seed,shuffle in pairs:
    aa=a.copy()
    if shuffle is not None:aa[ix['train']]=aa[ix['train']][np.random.default_rng(shuffle).permutation(len(ix['train']))]
    raw={'state':s,'action':aa,'real':np.c_[s,aa],'shuffled':np.c_[s,aa]}[base];mu=raw[ix['train']].mean(0);sd=raw[ix['train']].std(0)+1e-6;x=torch.tensor((raw-mu)/sd)
    if cls=='linear':pred=fit_linear(x,y,ix['train']);out['models'].append({'class':cls,'baseline':base,'seed':None,'shuffle_seed':shuffle,'test':metrics(pred(x[ix['test']]),y[ix['test']])})
    else:n,e,v=fit_mlp(x,y,ix['train'],ix['validation'],seed);out['models'].append({'class':cls,'baseline':base,'seed':seed,'shuffle_seed':shuffle,'epochs':e,'validation_mse':v,'test':metrics(n(x[ix['test']]),y[ix['test']])})
 # Audit only: test constant direction and train-target state centroid identification.
 constant=torch.tensor(np.repeat(y[ix['train']].mean(0,keepdims=True).numpy(),len(ix['test']),0)); train_even=ix['train'][np.array([rows[i]['sample_id']%2==0 for i in ix['train']])];train_odd=ix['train'][np.array([rows[i]['sample_id']%2==1 for i in ix['train']])];centroids=np.array([s[train_even][ids[train_even]==t].mean(0) for t in range(16)]);pred=np.argmin(((s[train_odd,None,:]-centroids[None,:,:])**2).sum(2),1);out['target_proxy_audit']={'constant_direction_test':metrics(constant,y[ix['test']]),'within_train_target_nearest_centroid_accuracy':float((pred==ids[train_odd]).mean()),'chance_accuracy':1/16,'note':'audit-only; target ID never enters any probe input'}
 OUT.write_text(json.dumps(out,indent=2));print(json.dumps({'models':len(out['models']),'target_proxy_audit':out['target_proxy_audit']},indent=2))
if __name__=='__main__':main()
