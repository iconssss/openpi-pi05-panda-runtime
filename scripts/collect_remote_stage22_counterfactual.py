"""Audit then collect the frozen Stage 22 counterfactual pi05 dataset.

The stored learner schema is deliberately restricted to joint_position and
action_feature; labels remain labels and are never assembled as probe inputs.
"""
from __future__ import annotations
import argparse, hashlib, json
from itertools import combinations
from pathlib import Path
from time import perf_counter
import mujoco, numpy as np
from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport
from openpi_robot_runtime.stage21a import action_feature
from openpi_robot_runtime.stage22 import DIRECTIONS, split
from run_remote_pi05_panda_mismatch_diagnosis import VISUAL_CONDITIONS, apply_visual_variant, as_frame, free_camera, handles

ROOT=Path('/root/shared-nvme/openpi-robot-runtime'); XML=ROOT/'assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml'
OUT=ROOT/'results/stage22_counterfactual_intent'; SEED=20260822
PROMPT='Move the Panda end effector to the visible target safely in simulation.'
FORBIDDEN=('+x','-x','+y','-y','+z','-z','cartesian','coordinate','0.1')

def group_state(model,data,qpos,limits,group):
 key=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_KEY,'home'); mujoco.mj_resetDataKeyframe(model,data,key); mujoco.mj_forward(model,data)
 rng=np.random.default_rng(SEED+group); base=np.array([data.qpos[a] for a in qpos]); delta=rng.uniform(-.10,.10,7)
 value=np.array([np.clip(base[i]+delta[i],*limits[i]) for i in range(7)])
 for a,v in zip(qpos,value,strict=True): data.qpos[a]=v
 mujoco.mj_forward(model,data); return tuple(float(data.qpos[a]) for a in qpos)
def set_target(model,data,hand,target,direction):
 expected=data.xpos[hand].copy()+.10*np.array(direction); data.mocap_pos[int(model.body_mocapid[target])]=expected; mujoco.mj_forward(model,data); return expected
def render(renderer,data,condition,rng,wrist):
 renderer.update_scene(data,camera=free_camera(condition.exterior_azimuth,condition.exterior_elevation,condition.exterior_distance)); exterior=apply_visual_variant(renderer.render().copy(),condition,rng)
 renderer.update_scene(data,camera=wrist); return exterior,apply_visual_variant(renderer.render().copy(),condition,rng)
def audit(model,data,qpos,limits,hand,target,renderer,wrist):
 assert not any(x in PROMPT.lower() for x in FORBIDDEN)
 details=[]
 for group in (0,1):
  state=group_state(model,data,qpos,limits,group); hashes=[]
  for name,direction in DIRECTIONS.items():
   expected=set_target(model,data,hand,target,direction); actual=data.xpos[target].copy(); exterior,_=render(renderer,data,VISUAL_CONDITIONS[0],np.random.default_rng(SEED+group),wrist)
   hashes.append(hashlib.sha256(exterior.tobytes()).hexdigest()); details.append({'group':group,'condition':name,'state':state,'target_error_m':float(np.max(abs(actual-expected))),'image_hash':hashes[-1]})
  assert len(set(hashes))==6
 report={'passed':True,'prompt':PROMPT,'forbidden_prompt_tokens':FORBIDDEN,'groups_checked':2,'six_unique_images_per_group':True,'max_target_error_m':max(x['target_error_m'] for x in details),'details':details}
 (OUT/'task_condition_audit.json').write_text(json.dumps(report,indent=2)); return report
def infer(policy,exterior,wrist,state):
 start=perf_counter(); response=policy.infer(DroidObservation(as_frame(exterior),as_frame(wrist),DroidRobotState(state,.5),PROMPT)); chunk=tuple(tuple(float(x) for x in a) for a in response.action_chunk.actions); return chunk,(perf_counter()-start)*1000
def main():
 p=argparse.ArgumentParser(); p.add_argument('--mode',choices=('audit','pilot','full'),required=True); args=p.parse_args(); OUT.mkdir(parents=True,exist_ok=True)
 model=mujoco.MjModel.from_xml_path(str(XML)); data=mujoco.MjData(model); qpos,_,_,_,limits,hand,target=handles(model); renderer=mujoco.Renderer(model,height=256,width=256); wrist=free_camera(30,-10,.65)
 audit_report=audit(model,data,qpos,limits,hand,target,renderer,wrist)
 if args.mode=='audit': print(json.dumps(audit_report,indent=2)); return
 transport=ProcessOwnedTransport(OpenPIWebsocketTransportFactory('127.0.0.1',8000),request_timeout_seconds=5.,startup_timeout_seconds=15.); policy=OfficialOpenPIDroidClient(transport,timeout_seconds=5.,transport_is_thread_confined=True)
 try:
  # First server request is warm-up and deliberately not part of pilot/full data.
  state=group_state(model,data,qpos,limits,0); set_target(model,data,hand,target,DIRECTIONS['+x']); a,b=render(renderer,data,VISUAL_CONDITIONS[0],np.random.default_rng(SEED),wrist); infer(policy,a,b,state)
  rows=[]; groups=range(1) if args.mode=='pilot' else range(20); visuals=VISUAL_CONDITIONS[:1] if args.mode=='pilot' else VISUAL_CONDITIONS[:4]
  for group in groups:
   state=group_state(model,data,qpos,limits,group)
   for condition,direction in DIRECTIONS.items():
    expected=set_target(model,data,hand,target,direction)
    for visual_index,visual in enumerate(visuals):
     exterior,wrist_image=render(renderer,data,visual,np.random.default_rng(SEED+group*100+visual_index),wrist)
     try:
      chunk,rtt=infer(policy,exterior,wrist_image,state)
      rows.append({'group_id':group,'split':split(group),'condition':condition,'visual_condition':visual.name,'joint_position':state,'gripper_position':.5,'teacher_cartesian_unit_direction':direction,'action_feature':action_feature(chunk),'action_chunk':chunk,'rtt_ms':rtt,'safe_hold':None})
     except Exception as exc: rows.append({'group_id':group,'split':split(group),'condition':condition,'visual_condition':visual.name,'joint_position':state,'teacher_cartesian_unit_direction':direction,'safe_hold':f'{type(exc).__name__}: {exc}'})
 finally: transport.close(force=True)
 good=[r for r in rows if r['safe_hold'] is None]; actions=[np.array(r['action_chunk'][0]) for r in good]; max_delta=max((float(np.linalg.norm(a-b)) for a,b in combinations(actions,2)),default=0.)
 report={'mode':args.mode,'seed':SEED,'requested':len(groups)*6*len(visuals),'completed':len(good),'safe_holds':len(rows)-len(good),'pilot_max_first_action_pairwise_l2':max_delta,'pilot_gate_passed':args.mode!='pilot' or (len(good)==6 and max_delta>1e-4),'probe_feature_schema':['joint_position','action_feature'],'rows':rows}
 (OUT/('pilot.json' if args.mode=='pilot' else 'data.json')).write_text(json.dumps(report,indent=2)); print(json.dumps({k:report[k] for k in report if k!='rows'},indent=2))
 if args.mode=='pilot' and not report['pilot_gate_passed']: raise SystemExit('Pilot action-diversity gate failed')
if __name__=='__main__': main()
