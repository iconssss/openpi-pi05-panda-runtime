"""Collect frozen pi05 outputs and Cartesian labels; labels are never model inputs."""
from __future__ import annotations
import json
from itertools import product
from pathlib import Path
import mujoco, numpy as np
from openpi_robot_runtime.observation_builder import DroidObservation, DroidRobotState
from openpi_robot_runtime.official_openpi import OfficialOpenPIDroidClient
from openpi_robot_runtime.remote_client import OpenPIWebsocketTransportFactory, ProcessOwnedTransport
from openpi_robot_runtime.stage21a import action_feature, split_for_target
from run_remote_pi05_panda_mismatch_diagnosis import PROMPT, VISUAL_CONDITIONS, apply_visual_variant, as_frame, free_camera, handles, reset

TASK_XML=Path('/root/shared-nvme/openpi-robot-runtime/assets/panda_menagerie/franka_emika_panda/project02_reach_task.xml'); OUT=Path('/root/shared-nvme/openpi-robot-runtime/results/stage21a_cartesian_probe/data.json')
TARGETS=tuple((x,y,z) for x,y,z in product((.055,.07,.085,.10),(-.03,-.045,-.06),(.01,.02))); SEED=20260821; PER_TARGET=60
def main():
 OUT.parent.mkdir(parents=True,exist_ok=True); model=mujoco.MjModel.from_xml_path(str(TASK_XML)); data=mujoco.MjData(model); qpos,_,_,_,limits,hand,target=handles(model); renderer=mujoco.Renderer(model,height=256,width=256); wrist=free_camera(30,-10,.65); rng=np.random.default_rng(SEED); transport=ProcessOwnedTransport(OpenPIWebsocketTransportFactory('127.0.0.1',8000),request_timeout_seconds=5.,startup_timeout_seconds=10.); policy=OfficialOpenPIDroidClient(transport,timeout_seconds=5.,transport_is_thread_confined=True); rows=[]
 try:
  for target_id,offset in enumerate(TARGETS):
   for sample in range(PER_TARGET):
    metric=reset(model,data,hand,target,offset)
    for address,limit in zip(qpos,limits,strict=True): data.qpos[address]=np.clip(data.qpos[address]+rng.uniform(-.12,.12),*limit)
    mujoco.mj_forward(model,data); condition=VISUAL_CONDITIONS[(target_id*PER_TARGET+sample)%len(VISUAL_CONDITIONS)]; exterior_camera=free_camera(condition.exterior_azimuth,condition.exterior_elevation,condition.exterior_distance); renderer.update_scene(data,camera=exterior_camera); exterior=apply_visual_variant(renderer.render().copy(),condition,rng); renderer.update_scene(data,camera=wrist); wrist_image=apply_visual_variant(renderer.render().copy(),condition,rng); state=tuple(float(data.qpos[a]) for a in qpos); error=np.asarray(metric.target_position)-data.xpos[hand]; label=tuple(float(v) for v in error/max(float(np.linalg.norm(error)),1e-9))
    try:
     response=policy.infer(DroidObservation(as_frame(exterior),as_frame(wrist_image),DroidRobotState(state,.5),PROMPT)); chunk=tuple(tuple(float(v) for v in a) for a in response.action_chunk.actions); rows.append({'sample_id':len(rows),'target_id':target_id,'split':split_for_target(target_id),'target_offset_m':offset,'visual_condition':condition.name,'joint_position':state,'gripper_position':.5,'action_chunk':chunk,'action_feature':action_feature(chunk),'hand_position_m':tuple(float(v) for v in data.xpos[hand]),'target_position_m':metric.target_position,'teacher_cartesian_unit_direction':label,'safe_hold':None})
    except Exception as e: rows.append({'sample_id':len(rows),'target_id':target_id,'split':split_for_target(target_id),'safe_hold':f'{type(e).__name__}: {e}'})
 finally: transport.close(force=True)
 report={'scope':'Stage 21A frozen pi05 Cartesian intent dataset; target/hand positions are labels-only and forbidden probe inputs','seed':SEED,'targets':TARGETS,'per_target':PER_TARGET,'requested':len(TARGETS)*PER_TARGET,'completed':sum(r['safe_hold'] is None for r in rows),'safe_holds':sum(r['safe_hold'] is not None for r in rows),'rows':rows}; OUT.write_text(json.dumps(report,indent=2)); print(json.dumps({k:report[k] for k in ('requested','completed','safe_holds')},indent=2))
if __name__=='__main__': main()
