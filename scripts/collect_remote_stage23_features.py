"""One-pass Stage 23 feature extraction on immutable Stage 22 observations."""
from __future__ import annotations
import argparse,json
from itertools import combinations
from pathlib import Path
import mujoco,numpy as np
from openpi_robot_runtime.observation_builder import DroidObservationBuilder, DroidObservation, DroidRobotState, RGBFrame
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory,ProcessOwnedTransport
from openpi_robot_runtime.stage21a import action_feature
from openpi_robot_runtime.stage22 import DIRECTIONS,split
from collect_remote_stage22_counterfactual import XML,SEED,PROMPT,group_state,set_target,render
from run_remote_pi05_panda_mismatch_diagnosis import VISUAL_CONDITIONS,as_frame,free_camera,handles
OUT=Path('/root/shared-nvme/openpi-robot-runtime/results/stage23_upstream_representation')
def wire(exterior,wrist,state):
 request=DroidObservationBuilder().build(DroidObservation(as_frame(exterior),as_frame(wrist),DroidRobotState(state,.5),PROMPT))
 def image(value):
  assert isinstance(value,RGBFrame); return np.frombuffer(value.data,dtype=np.uint8).reshape((value.height,value.width,value.channels)).copy()
 return {'observation/exterior_image_1_left':image(request['observation/exterior_image_1_left']),'observation/wrist_image_left':image(request['observation/wrist_image_left']),'observation/joint_position':np.asarray(request['observation/joint_position'],dtype=np.float32),'observation/gripper_position':np.asarray(request['observation/gripper_position'],dtype=np.float32),'prompt':request['prompt']}
def get(transport,exterior,wrist,state):
 payload=transport.infer(wire(exterior,wrist,state)); actions=tuple(tuple(float(x) for x in a) for a in payload['actions']); return payload,actions
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=('pilot','full'),required=True); args=ap.parse_args(); OUT.mkdir(parents=True,exist_ok=True)
 model=mujoco.MjModel.from_xml_path(str(XML)); data=mujoco.MjData(model); qpos,_,_,_,limits,hand,target=handles(model); renderer=mujoco.Renderer(model,height=256,width=256); wrist=free_camera(30,-10,.65); transport=ProcessOwnedTransport(OpenPIWebsocketTransportFactory('127.0.0.1',8000),request_timeout_seconds=5.,startup_timeout_seconds=15.); rows=[]
 try:
  # No-control warm-up; discarded.
  state=group_state(model,data,qpos,limits,0); set_target(model,data,hand,target,DIRECTIONS['+x']); a,b=render(renderer,data,VISUAL_CONDITIONS[0],np.random.default_rng(SEED),wrist); get(transport,a,b,state)
  groups=range(1) if args.mode=='pilot' else range(20); visuals=VISUAL_CONDITIONS[:1] if args.mode=='pilot' else VISUAL_CONDITIONS[:4]
  for g in groups:
   state=group_state(model,data,qpos,limits,g)
   for condition,direction in DIRECTIONS.items():
    set_target(model,data,hand,target,direction)
    for vi,visual in enumerate(visuals):
     exterior,wrist_image=render(renderer,data,visual,np.random.default_rng(SEED+g*100+vi),wrist)
     try:
      payload,actions=get(transport,exterior,wrist_image,state); feats={k:np.asarray(payload[k],dtype=np.float16) for k in ('stage23_prefix','stage23_action_expert','stage23_preoutput')}; rows.append({'group_id':g,'split':split(g),'condition':condition,'visual_condition':visual.name,'joint_position':state,'gripper_position':.5,'teacher_cartesian_unit_direction':direction,'action_feature':action_feature(actions),'stage23_features':{k:v.tolist() for k,v in feats.items()},'safe_hold':None})
     except Exception as exc: rows.append({'group_id':g,'split':split(g),'condition':condition,'safe_hold':f'{type(exc).__name__}: {exc}'})
 finally: transport.close(force=True)
 good=[r for r in rows if r['safe_hold'] is None]; report={'mode':args.mode,'requested':len(groups)*6*len(visuals),'completed':len(good),'safe_holds':len(rows)-len(good),'feature_shapes':{k:list(np.asarray(good[0]['stage23_features'][k]).shape) for k in good[0]['stage23_features']} if good else {},'preoutput_identical_to_action_expert':all(np.array_equal(np.asarray(r['stage23_features']['stage23_preoutput']),np.asarray(r['stage23_features']['stage23_action_expert'])) for r in good),'rows':rows}
 if args.mode=='pilot':
  report['max_action_pairwise_l2']=max(float(np.linalg.norm(np.asarray(a['action_feature'][:8])-np.asarray(b['action_feature'][:8]))) for a,b in combinations(good,2)); report['feature_pairwise_max_l2']={k:max(float(np.linalg.norm(np.asarray(a['stage23_features'][k])-np.asarray(b['stage23_features'][k]))) for a,b in combinations(good,2)) for k in good[0]['stage23_features']}; report['finite']=all(np.isfinite(np.asarray(r['stage23_features'][k])).all() and np.asarray(r['stage23_features'][k]).std()>0 for r in good for k in r['stage23_features']); report['pilot_passed']=len(good)==6 and report['finite'] and max(report['feature_pairwise_max_l2'].values())>1e-4
 (OUT/('pilot.json' if args.mode=='pilot' else 'data.json')).write_text(json.dumps(report)); print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
 if args.mode=='pilot' and not report['pilot_passed']: raise SystemExit('Stage23 pilot gate failed')
if __name__=='__main__': main()
