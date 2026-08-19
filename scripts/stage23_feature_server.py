"""Checkpoint-preserving Stage 23 feature side-channel policy server."""
from __future__ import annotations
import dataclasses, logging, socket, time
import einops, jax, jax.numpy as jnp, numpy as np, tyro
from flax import nnx
from openpi.models import model as _model
from openpi.models.pi0 import make_attn_mask
from openpi.policies import policy as _policy
from openpi.policies import policy_config as _policy_config
from openpi.serving import websocket_policy_server
from openpi.shared import nnx_utils
from openpi.training import config as _config

def sample_with_features(self,rng,observation,*,num_steps=10,noise=None):
 observation=_model.preprocess_observation(None,observation,train=False); dt=-1./num_steps; batch=observation.state.shape[0]
 if noise is None: noise=jax.random.normal(rng,(batch,self.action_horizon,self.action_dim))
 prefix_tokens,prefix_mask,prefix_ar=self.embed_prefix(observation); prefix_attn=make_attn_mask(prefix_mask,prefix_ar); positions=jnp.cumsum(prefix_mask,axis=1)-1
 (prefix_out,_),kv_cache=self.PaliGemma.llm([prefix_tokens,None],mask=prefix_attn,positions=positions)
 prefix_pool=jnp.sum(prefix_out*prefix_mask[...,None],axis=1)/jnp.maximum(prefix_mask.sum(axis=1,keepdims=True),1)
 def step(carry):
  x_t,time,_=carry; suffix_tokens,suffix_mask,suffix_ar,adarms=self.embed_suffix(observation,x_t,jnp.broadcast_to(time,batch)); suffix_attn=make_attn_mask(suffix_mask,suffix_ar); prefix_attn2=einops.repeat(prefix_mask,'b p -> b s p',s=suffix_tokens.shape[1]); full=jnp.concatenate([prefix_attn2,suffix_attn],axis=-1); positions=jnp.sum(prefix_mask,axis=-1)[:,None]+jnp.cumsum(suffix_mask,axis=-1)-1
  (_,suffix_out),_=self.PaliGemma.llm([None,suffix_tokens],mask=full,positions=positions,kv_cache=kv_cache,adarms_cond=[None,adarms]); final=suffix_out[:,-self.action_horizon:]; velocity=self.action_out_proj(final)
  return x_t+dt*velocity,time+dt,final
 def cond(carry): return carry[1]>=-dt/2
 init=jnp.zeros((batch,self.action_horizon,self.action_out_proj.in_features),dtype=jnp.bfloat16)
 x0,_,final=jax.lax.while_loop(cond,step,(noise,jnp.array(1.),init)); expert_pool=jnp.mean(final,axis=1)
 return x0,prefix_pool,expert_pool,expert_pool

class FeaturePolicy(_policy.Policy):
 def __init__(self,base): self.__dict__=base.__dict__; self._sample_features=nnx_utils.module_jit(sample_with_features.__get__(self._model,type(self._model)))
 def infer(self,obs,*,noise=None):
  inputs=jax.tree.map(lambda x:x,obs); inputs=self._input_transform(inputs); inputs=jax.tree.map(lambda x:jnp.asarray(x)[None,...],inputs); self._rng,rng=jax.random.split(self._rng); observation=_model.Observation.from_dict(inputs); start=time.monotonic(); actions,prefix,expert,pre=self._sample_features(rng,observation,noise=noise) if noise is not None else self._sample_features(rng,observation); elapsed=time.monotonic()-start
  outputs={'state':inputs['state'],'actions':np.asarray(actions[0]),'stage23_prefix':np.asarray(prefix[0],dtype=np.float16),'stage23_action_expert':np.asarray(expert[0],dtype=np.float16),'stage23_preoutput':np.asarray(pre[0],dtype=np.float16)}; transformed=self._output_transform({'state':outputs['state'],'actions':outputs['actions']}); transformed.update({k:outputs[k] for k in ('stage23_prefix','stage23_action_expert','stage23_preoutput')}); transformed['policy_timing']={'infer_ms':elapsed*1000}; return transformed

@dataclasses.dataclass
class Args: port:int=8000; policy_config:str='pi05_droid'; policy_dir:str='/root/shared-nvme/openpi-robot-runtime/openpi-cache/openpi-assets/checkpoints/pi05_droid'
def main(args):
 base=_policy_config.create_trained_policy(_config.get_config(args.policy_config),args.policy_dir); policy=FeaturePolicy(base); logging.info('Stage23 feature server: prefix/action-expert/pre-output side channel only; weights frozen')
 websocket_policy_server.WebsocketPolicyServer(policy=policy,host='0.0.0.0',port=args.port,metadata=policy.metadata).serve_forever()
if __name__=='__main__': logging.basicConfig(level=logging.INFO,force=True); main(tyro.cli(Args))
