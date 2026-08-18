# Stage 0 — OpenPI 官方源码调查

日期：2026-08-16
范围：只读源码与官方文档调查；无安装、无 checkpoint 下载、无 GPU 操作。

## 核心结论

官方已有完整 remote inference path，项目应复用而不是重写：

```text
robot runtime
  → openpi_client.websocket_client_policy.WebsocketClientPolicy
  → WebSocket / MessagePack NumPy
  → openpi.serving.websocket_policy_server.WebsocketPolicyServer
  → policy.infer(observation)
  → {"actions": action_chunk, timing fields}
```

## 源码定位

| 主题 | 官方文件 | 结论 |
|---|---|---|
| Server entrypoint | `scripts/serve_policy.py` | 默认绑定 `0.0.0.0:8000`，选择 config/checkpoint 后启动 WebSocket server。 |
| Server protocol | `src/openpi/serving/websocket_policy_server.py` | MessagePack request/response；`/healthz`；response 注入 `server_timing.infer_ms`。 |
| Robot client | `packages/openpi-client/src/openpi_client/websocket_client_policy.py` | 轻量 client；连接后接收 metadata；`infer(dict)` 返回 dict。 |
| Policy path | `src/openpi/policies/policy.py` | 输入 transform → model `sample_actions` → output transform；输出 `policy_timing.infer_ms`。 |
| Norm stats | `src/openpi/policies/policy_config.py`, `src/openpi/transforms.py` | checkpoint assets 中的 stats 驱动 Normalize / Unnormalize。 |
| DROID contract | `src/openpi/policies/droid_policy.py` | 输入为两相机、7 joint positions、1 gripper position；输出截取 8 维。 |
| DROID runtime | `examples/droid/main.py` | action 在示例中是 7 joint velocity + 1 gripper position，包含 clipping 与 receding horizon。 |

## 数据流

```text
raw embodiment observation
  → embodiment input transform
  → normalized / padded model space
  → π0.5 flow sampling
  → unnormalize
  → embodiment output transform
  → action chunk for that embodiment
```

因此，动作 adapter 要处理 **policy embodiment output → target robot SDK**；不得绕过 checkpoint norm stats，也不得假定所有 π0.5 action 都是 EEF pose。

## 版本与资源判断

- 完整 server：Python >=3.11；官方 pyproject currently pins `jax[cuda12]==0.5.3`、`torch==2.7.1`、`transformers==4.53.2`。
- 官方推理显存估计：>8 GB；当前 4090 足够，但它正在服务 ACT，不能并发启动。
- 官方只声明测试 Ubuntu 22.04；robot-cloud Ubuntu 24.04 需后续隔离 smoke test。
- 当前必须使用独立 OpenPI 环境与独立持久化存储路径。

## 风险发现

`pi05_droid` config 的 action horizon 为 15，而 DROID example 断言 `(10, 8)`。后续 runtime 以真实 response metadata / shape validation 为准，绝不写死 horizon。
