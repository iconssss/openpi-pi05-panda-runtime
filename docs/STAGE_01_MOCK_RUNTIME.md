# Stage 1 — Mock Closed-Loop Runtime

日期：2026-08-16
范围：纯标准库、CPU-only。没有 OpenPI install、模型、网络或 GPU。

## 要解决的问题

先验证真正重要的系统所有权：policy 只预测 action chunk；robot runtime 决定执行多少步、如何适配、何时拒绝及何时再规划。

## 实现

```text
Observation
  → DeterministicFakePolicyClient
  → ActionChunk.validate
  → MockDroidAdapter
  → DroidLikeSafetyFilter
  → MockDroidRobot.execute
  → next Observation
```

`ClosedLoopRuntime.run()` 的策略为：预测 `H` 步，仅执行 `min(k, H, remaining)` 步，然后构造新 observation 再请求一次 policy。

## 验证标准

`tests/test_closed_loop.py` 覆盖：

1. `H=3, k=2, total=5` 时恰好产生 3 次 policy request，证明不是一次性 open-loop。
2. 超范围 joint velocity 与 gripper position 在执行前被 clipping。
3. 错误 action dimension 在进入 mock robot 前被拒绝，执行命令列表保持为空。

## 面试表达

这一步的价值不是“假模型能控制机器人”，而是证明 runtime 的责任边界可单独测试：

- 模型服务无权直接调用 SDK；
- action chunk 的 `H` 与 execution horizon `k` 解耦；
- action safety 是数据类型和动作单位确定后的 robot-side 必经层；
- 更换 policy client 不应影响 adapter、safety 或 receding-horizon loop。

## Stage 1b 增量（已完成）

- `DroidObservationBuilder`：固定为官方 DROID public request keys；输入帧必须由上游处理成 `224×224×3` RGB。
- `BoundedRemotePolicyClient`：为官方同步 client 增加 deadline 分类。超时后的安全语义是 hold/reconnect，不是继续执行旧 chunk。
- `InferenceMetric` / JSONL：为后续比较 client round-trip、server infer、policy infer、timeout/failure rate 提供持久化记录。

## 下一小步

在 GPU 空闲后，先提出独立 OpenPI environment 的安装计划（Python/JAX/PyTorch、安装位置、预计磁盘、可卸载性与对现有项目的影响），获准后才安装并做远端 smoke test。
