# 项目记忆 / 长期决策记录

## 2026-08-18 — Stage 3 completed: official server plus closed-loop integration

- The official GCS manifest for `pi05_droid` was checked object-by-object:
  20 expected objects, total `12,429,488,598` bytes, all path/size checks
  passed. No `.openpi-download-partial` remains.
- The checkpoint is retained at
  `/root/shared-nvme/openpi-robot-runtime/openpi-cache/openpi-assets/checkpoints/pi05_droid`.
  Two unrelated busy `.nfs*` files in that tree must not be deleted or moved
  without separately identifying their holder.
- Official server validation passed: checkpoint restore (~19 s), `/healthz`
  HTTP 200, and the official DROID client completed one request. Its saved
  timing artifact is
  `/root/shared-nvme/openpi-robot-runtime/results/pi05_droid_official_smoke_timings.parquet`.
- Project code now contains `OfficialOpenPIDroidClient`: typed DROID
  observation -> official WebSocket payload -> validated finite `(H, 8)` action
  chunk, with a robot-side timeout wrapper. `StaticFrameOpenPIBridge` connects
  it to the existing closed-loop mock runtime without adding local GPU/OpenPI
  dependencies.
- Real remote integration smoke result is retained at
  `/root/shared-nvme/openpi-robot-runtime/results/project_runtime_closed_loop_smoke.json`.
  It completed two requests and two mock executions with `k=1`, so the second
  request consumed re-observed mock joint state. Measured client round trips:
  103.84 ms and 87.72 ms; server inference: 100.97 ms and 85.80 ms; policy
  inference: 58.99 ms and 57.66 ms.
- Scope is strictly software-only: static zero RGB frames + `MockDroidRobot`.
  It establishes protocol, safety-boundary, and receding-horizon integration;
  it does not establish camera performance, simulator task success, physical
  robot control, or safety certification.
- The server was stopped via SIGTERM after result collection, releasing the
  ~20.9 GB model allocation. Do not leave it running while there is no active
  inference experiment.

## 2026-08-18 — Stage 4: request-cadence ablation and client compatibility fix

- With all inputs fixed and four mock execution steps, `k=1` issued four policy
  requests (mean client RTT 86.59 ms); `k=2` issued two (79.40 ms). The result
  artifact is `/root/shared-nvme/openpi-robot-runtime/results/execution_horizon_ablation.json`.
  This is a systems measurement only, not manipulation quality or safety proof.
- An integration defect was found honestly: the official synchronous
  `WebsocketClientPolicy` creates its WebSocket during construction and cannot
  reliably be called from the generic timeout worker thread. The server and
  official simple client remained healthy; only the cross-thread project call
  hung. `OfficialOpenPIDroidClient(transport_is_thread_confined=True)` now
  invokes this transport on its owning thread.
- The generic `BoundedRemotePolicyClient` remains tested for transports that are
  safe to execute in a worker. A production hard timeout for the official client
  remains future work: use a cancellable transport or a dedicated process that
  owns, aborts, and reconnects the WebSocket after an unconfirmed request.
- The temporary server was SIGTERM-stopped after results were saved. Final
  verification: no GPU process, 1 MiB / 24564 MiB allocated, shared disk 21 GB
  available.

## 2026-08-18 — Stage 5: GPU-backed inference latency profile

- After three warmups, 60 sequential real π0.5 DROID-schema requests measured
  mean / p95 client RTT of 78.54 / 81.49 ms, server inference 77.75 / 80.61 ms,
  and policy inference 55.79 / 56.15 ms. Artifact:
  `/root/shared-nvme/openpi-robot-runtime/results/pi05_droid_latency_profile.json`.
- GPU trace contains 368 100-ms samples. During active inference, utilization
  reached 79–81%, memory was ~20.9 GB, and draw ~267–269 W. Mixed idle samples
  remain in the artifact; do not present an average as active-only utilization.
- Three prompts generated different first action vectors, which verifies prompt
  flow through the request; static zero images and fixed state prevent any claim
  of visual/task performance.
- Server was SIGTERM-stopped after the profile. Final check: 0% GPU, 1 MiB
  memory, 21 GB shared-disk free.

## 2026-08-18 — Stage 6: fail-safe behavior after policy failure

- `ClosedLoopRuntime` now converts any policy/action/adapter/safety exception
  into one traceable mock safe hold and terminates that run before a further
  command is executed. This design is verified locally and does not claim a
  physical robot emergency-stop implementation.
- Remote test: one confirmed real π0.5 response yielded one mock command; a
  controlled `ConnectionError` before the next request yielded exactly one safe
  hold, zero additional mock commands, and `pass=true`. Artifact:
  `/root/shared-nvme/openpi-robot-runtime/results/policy_fault_injection.json`.
- Final post-test state: temporary server stopped, 4090 0% / 1 MiB, shared
  disk 21 GB free. The next meaningful safety increment is a process-owned,
  cancellable WebSocket transport for genuine unresponsive-socket deadlines.

## 2026-08-18 — Stage 7: confirmed deadline and reconnect boundary

- `ProcessOwnedTransport` makes a child process own the official synchronous
  WebSocket. Timeout terminates that child; recovery needs a new process/socket.
  No new package was installed.
- Remote validation passed normal H=15 response, forced 1-ms deadline with one
  safe hold and zero mock commands, then fresh-process recovery H=15. Artifact:
  `/root/shared-nvme/openpi-robot-runtime/results/process_transport_deadline.json`.
- On remote Ubuntu, forced spawn hung before inference; the native fork default
  passed. The code uses platform defaults unless explicitly overridden.

## 2026-08-18 — Stage 8: simulator preflight

- Project 2's existing OpenPI environment already includes MuJoCo 2.3.7,
  dm-control, gymnasium, gym-aloha and image libraries; no Python install is
  needed. The old ACT environment is absent and not reused.
- ALOHA TransferCube is a 14-action dual-arm environment with one top camera;
  it is incompatible by default with π0.5-DROID's 8-action single-arm contract.
  Any evaluation needs an explicit limited adapter, never an equivalence claim.
- EGL headless smoke failed before reset at PyOpenGL EGL import. No files or
  environments were changed. Candidate repair is minimal system `libegl1` /
  `libgl1` install, requiring explicit permission because it writes system disk.

## 2026-08-18 — Stage 8: EGL repair and ALOHA interface rejection

- With explicit approval, installed system `libegl1` and `libgl1` (dependency
  chain ~55 MB download / 234 MB system disk). The shared persistent disk,
  OpenPI environment, checkpoints, and other projects remained untouched.
- EGL headless ALOHA smoke passed: reset + five zero action steps + top camera
  render. Artifact is under `results/aloha_headless_smoke/` on shared storage.
- Formal compatibility decision: ALOHA's 14 normalized / 16 underlying
  dual-arm target controls and single camera are not a valid direct target for
  π0.5-DROID's 8 single-arm action outputs and two images. No direct policy
  task evaluation will be claimed. No Panda/Franka asset exists locally.

最后更新：2026-08-16（Stage 1b）

## 项目身份

- 名称：OpenPI π0.5 VLA Remote Inference & Robot Action Adapter。
- 目标：证明并解释 `observation → remote policy → action chunk → adapter → safety → execution → next observation` 的工程闭环。
- 面试定位：展示 VLA system engineering，而不是复现训练或只打印 action tensor。

## 不可违背的工程约束

- 现有 LeRobot + ACT 项目、其环境、dataset、HF cache 与运行中的 4090 实验均不干扰。
- 不复用 `/root/shared-nvme/conda-envs/lerobot-act`；未来 OpenPI 使用独立环境。
- 未来远端项目路径：`/root/shared-nvme/openpi-robot-runtime/`。
- 未来环境路径：`/root/shared-nvme/conda-envs/openpi-runtime/`。
- 未来 OpenPI cache 必须隔离到 `/root/shared-nvme/hf-cache-openpi/` 或经确认的 `OPENPI_DATA_HOME` 路径；下载前先检查共享盘容量。
- 4090 正在服务 ACT；在确认其完成前不加载 π0.5、不下载大权重、不做重型 GPU 工作。需要第二实例时先说明预计 GPU 小时与约 2 RMB/h 的成本，再由用户决定。

## 已确认的官方事实（2026-08-16）

- 官方仓库：`Physical-Intelligence/openpi`。
- OpenPI 已提供 `WebsocketPolicyServer`、`WebsocketClientPolicy`、MessagePack/NumPy serialization 和 `/healthz`。
- server response 可包含 `server_timing.infer_ms` 与 `policy_timing.infer_ms`。
- 完整 OpenPI 当前要求 Python >=3.11，包含 JAX CUDA 12、PyTorch 2.7.1、Transformers 4.53.2；官方测试环境是 Ubuntu 22.04。
- `openpi-client` 依赖极少且不需要 GPU，可作为 robot-side dependency。
- π0.5 DROID 运行时的公开 contract 是 7 joint velocity + 1 gripper position；务必确认 selected checkpoint 的 transform 后再接真实硬件。

## 已知风险 / 待验证项

- robot-cloud 为 Ubuntu 24.04，不是官方声明的测试 OS，后续必须隔离验证。
- 官方源码中 `pi05_droid` 配置的 horizon 为 15，但 DROID example 仍对 `(10, 8)` 做断言；不能硬编码该数值。
- checkpoint 大小尚未测量，未来需要先检查 `/root/shared-nvme` 可用空间，再做明确下载计划。
- 当前 mock 只覆盖 DROID-like action contract，未声称适配任何真实机器人。
- 2026-08-16 远端只读检查：RTX 4090 `0%`、显存使用 `1 MiB`；`/root/shared-nvme` 总 50 GB、已用 21 GB、可用约 30 GB。
- OpenPI runtime 的依赖、官方源码、模型 cache 与实验产物放在 `/root/shared-nvme`，而非 Windows D 盘或容器系统盘；Windows D 盘保留本项目 Git source、README 与设计记录。
- 2026-08-16 已创建 `/root/shared-nvme/conda-envs/openpi-runtime`（Python 3.11.15，约 205 MB）并把 Conda package cache 放在 `/root/shared-nvme/conda-pkgs`。`uv 0.12.5` 安装在此独立环境中。
- 远端基础 Mamba 因自身 Conda API 不匹配无法启动；基础 Conda 24.11.3 正常，因此只使用 Conda 创建本项目环境，不升级或修改基础 Mamba。
- 官方 OpenPI clone 正在拉取至 `/root/shared-nvme/openpi-robot-runtime/vendor/openpi`；远端 GitHub HTTPS 当前低速，尚未开始 `uv sync` 或模型下载。
- 远端 GitHub 不能继承 Windows `127.0.0.1:7897` 代理。OpenPI、LeRobot 和 dlimp 的固定源码快照均通过一次性 D 盘临时下载 + SCP 上传桥接，随后临时文件已删除；依赖源码只保留在 `/root/shared-nvme/openpi-robot-runtime/vendor/`。
- 为保证 `uv lock` 不再尝试 GitHub，isolated OpenPI vendor copy 的 `[tool.uv.sources]` 将 LeRobot 与 dlimp 指向对应 remote vendor snapshots。两者仍对应官方原始固定 commits；该网络适配仅影响本项目 vendor copy。
- 2026-08-16 已成功完成 OpenPI `--no-dev` runtime dependency sync。验证：`openpi` import 正常，JAX 0.5.3 看到 `CudaDevice(0)`，Torch 2.7.1+cu126 看到 RTX 4090。尚未下载 checkpoint、尚未加载 policy、尚未进行推理。
- 2026-08-17 项目 1 已清理后，shared-nvme 可用空间恢复至约 36 GB，4090 空闲。已启动官方 `pi05_droid` checkpoint 下载（12,429,488,598 bytes）到 `/root/shared-nvme/openpi-robot-runtime/openpi-cache/`；该下载不使用 GPU，日志位于 `logs/download_pi05_droid.log`。下载完成前不得启动 policy server。
- 2026-08-17 下载策略修订：远端 gcsfs 约 0.7 MiB/s；远端 curl 直连约 0.18 MiB/s；Windows 从 GCS 约 0.08 MiB/s、上传远端约 1.02 MiB/s，因此不采用本地中转。已清理失败 `gsutil rsync` 的 `.gstmp` 临时文件；shared-nvme 约剩余 31 GB。现运行受控脚本 `scripts/download_missing_pi05_droid.py`：按路径与字节数跳过 14 个完整对象，仅原子下载 6 个缺失分片（12,293,989,601 bytes）；预计约 5 小时，GPU 保持空闲。

## 阶段完成情况

- [x] Stage 0：官方工程、依赖、WebSocket、观测、归一化和动作链路只读调查。
- [x] Stage 1a：CPU-only fake policy + adapter + safety + mock robot 的闭环最小实现。
- [x] Stage 1b：production-shaped observation / timeout / metric artifact（reconnect policy 已设计，实际 WebSocket reconnect 待官方 client 接入）。
- [ ] Stage 2a：隔离 OpenPI environment 与官方 source checkout（environment 完成；source checkout 进行中）。
- [ ] Stage 2b：依赖同步与官方 client-server smoke test（待 source checkout、空间复核与 checkpoint 下载计划）。
- [ ] Stage 3：接入更真实的 simulator 或 mock task evaluation。
- [ ] Stage 4：latency / execution horizon ablation。
- [ ] Stage 5：面试导向 README、架构图、结果与限制说明。
## 2026-08-19 — Stage 18 frozen-policy residual-adapter held-out evaluation

- The evaluator locks Stage 17 held-out targets 8--11, six fixed visuals, 40
  steps/episode, raw identity, all frozen adapter seeds (11/22/33), and DLS.
  No held-out outcome tuned, selected, or retrained an adapter.
- 24 episodes per arm / 120 total all completed with zero safe holds and zero
  bridge clips. Success at 4 cm was 0/24 for raw, each seed, and DLS. Mean
  final distance: raw 0.17973 m; seeds 11/22/33: 0.10350/0.10159/0.10519 m;
  DLS 0.10194 m. This distance improvement is not task success; DLS is not a
  learned policy.
- Raw report stays only on remote shared storage:
  `/root/shared-nvme/openpi-robot-runtime/results/stage18_held_out_evaluation/report.json`.
  The run-specific policy server was SIGTERM-stopped; GPU was 0% / 1 MiB and
  shared disk had 21 GB free.
## 2026-08-19 — Stage 19 read-only multi-step failure attribution

- Stage 19 consumed only the frozen Stage 18 held-out JSON, with no GPU,
  policy server, policy request, training, tuning, or seed selection. The
  committed analyzer produces an ignored JSON/SVG artifact locally; raw data
  remains authoritative on remote shared storage.
- Raw identity mean distance worsened from 0.13601 m to 0.17973 m and added
  24.21 mm over the final ten steps. Seeds 11/22/33 and DLS improved net
  distance but then regressed +5.91/+2.62/+5.68/+7.10 mm over the final ten
  steps. All variants had zero safe holds and bridge clips.
- Visual and target grouping is descriptive only. Per-step residual vectors,
  Panda state-distribution shift, and joint-limit proximity were not logged;
  Stage 19 explicitly treats them as unidentifiable rather than causal claims.
  Stage 20 must pre-register a separate training distribution and independent
  test set before any new model is trained.
## 2026-08-19 — Stage 20 CPU-only Panda control feasibility ladder

- Stage 20 pre-registered a new four-target diagnostic split and separate
  four-target final split. It ran no pi05 server/request, adapter, or training;
  CUDA was disabled and GPU stayed idle.
- Diagnostic DLS selection: 40-step existing bridge was 0/4 (9.31 cm),
  120-step existing bridge 0/4 (13.03 cm), and 0.20-s/120-step bridge 4/4
  (3.91 cm), so only the last condition entered final test.
- Final: no-op 0/4, fixed raw-action bridge 0/4 (328 expected fixed-vector
  clips), DLS bridge 3/4 (4.12 cm mean), direct-position IK 4/4 (3.15 cm).
  The fourth DLS target stopped at 4.75 cm after 120 steps. The 4/4 feasibility
  condition failed, blocking Stage 21 training; this is not a pi05 conclusion.
## 2026-08-19 — Stage 20B low-level control-contract replication

- Stage 20B used entirely new development and final target offsets, logged a
  fixed seed (`20260819`) and direct-IK reachability residuals, and ran CPU-only
  MuJoCo with no pi05 server/request, GPU inference, adapter, or training.
- Diagnostic-only selection compared four declared DLS contracts. Only the
  Stage 20 reference condition reached 4/4 (3.82 cm); the three damped/slow
  alternatives were 0/4. The rule therefore froze the reference contract
  without viewing final-test outcomes.
- New final test: no-op 0/4, fixed raw-action bridge 0/4, frozen DLS velocity
  contract 4/4 (3.87 cm; 0 clips/events), direct-position IK 4/4 (3.17 cm).
  Final DLS IK residuals were 0.047--0.495 mm and success occurred in 5--8
  steps. This establishes only low-level analytic Panda simulator feasibility;
  it permits a separately pre-registered Stage 21 but proves no pi05, adapter,
  real-robot, calibration, sim-to-real, or safety-certification capability.
## 2026-08-19 — Stage 21A frozen Cartesian intent probe (negative)

- New frozen pi05 data: 1,440/1,440 rows, 0 safe holds, target-level 960/240/240
  train/validation/test. The feature was only 16-D first-action plus chunk mean;
  target/hand geometry remained labels-only. Server stopped before CPU probes.
- State+real pi05 MLP was worse in MSE (0.01369 ± 0.00023) than state-only
  (0.01133 ± 0.00042), and failed the locked gate against state-only and shuffled
  action. Stage 21B is blocked.
- State-to-target-ID nearest-centroid audit was 6.67% versus 6.25% chance: no
  target proxy evidence. Constant label direction cosine was already 0.84831,
  so the direction distribution is concentrated and cosine cannot stand alone
  as evidence of pi05 Cartesian intent.
## 2026-08-19 — Stage 22 counterfactual benchmark design (CPU-only)

- Stage 22 pre-registers 20 state groups with six exact same-state task
  conditions each: ±X, ±Y, ±Z. Groups—not individual pair members—split into
  train/validation/test, preventing cross-split counterfactual leakage.
- CPU audit passed: each split is direction-balanced, constant-direction cosine
  is 0, maximum within-group state delta is 0, and state-only condition chance
  is 1/6. Mock state-only pair discrimination is 0. No pi05 server, action
  collection, adapter training, or GPU use occurred.
- Recommended eventual collection is 20 groups × 6 conditions × 4 visual
  realizations = 480 frozen requests, only after explicit review/authorization.
