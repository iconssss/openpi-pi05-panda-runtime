# Stage 2a — Isolated Remote Environment

日期：2026-08-16
范围：创建独立 Python environment 与准备官方 OpenPI source checkout；不下载 checkpoint、不执行模型推理。

## 存储决定

| 内容 | 存储位置 | 原因 |
|---|---|---|
| 当前项目源码、README、设计与 Git history | Windows `D:\600-Robot\300-Project\200-Project02` | 本地开发与长期 source of truth。 |
| OpenPI Python environment | `/root/shared-nvme/conda-envs/openpi-runtime` | 4090 容器可访问，关机/实例释放后仍保留。 |
| Conda package cache | `/root/shared-nvme/conda-pkgs` | 避免大型 package cache 落到远端易失系统盘。 |
| Official OpenPI source | `/root/shared-nvme/openpi-robot-runtime/vendor/openpi` | 与本项目隔离，供 GPU server 使用。 |
| Future OpenPI cache / checkpoint | 本项目专用 shared-nvme 子目录 | 不与 ACT 的 HF cache 或 checkpoint 混用。 |

Windows D 盘不作为 remote GPU runtime 的依赖盘：该路径没有被确认以可靠、持久和高性能的方式挂载到 robot-cloud。将 JAX/Torch/OpenPI 依赖放在 D 盘也不能让远端容器直接使用。

## 与 ACT environment 的隔离理由

现有 `lerobot-act` 是已验证实验环境（Python 3.12、Torch 2.11 + CUDA 13、LeRobot 0.6）。OpenPI 的官方工程锁定不同依赖组合，并涉及 JAX CUDA 12、Torch 2.7.1、Transformers 4.53.2 与 Transformers source patch。复用或原地升级 ACT environment 会引入不可接受的版本污染风险。

## 已完成

- 已只读确认：4090 空闲（0% utilization、1 MiB used），shared-nvme 可用约 30 GB。
- 已创建独立 `openpi-runtime`：Python 3.11.15，environment directory 约 205 MB。
- 已将 Conda cache 定向到 shared-nvme；当前该 cache 约 2.2 GB。
- 已安装 `uv 0.12.5` 到 `openpi-runtime`（下载约 24 MB）。
- 基础 Mamba 启动失败，但基础 Conda 24.11.3 正常；未改动基础 Mamba。

## 进行中与边界

远端 GitHub HTTPS 无法使用 Windows 本机 `127.0.0.1:7897` 代理，直接 clone/fetch 会卡住。解决方案是仅将小型源码 archive 临时下载到 D 盘、通过 SCP 传到 shared-nvme、确认后立即删除本地临时文件。远端没有存储在 C 盘，也没有保留依赖源码的 D 盘副本。

为使 `uv` 不再尝试 GitHub，isolated OpenPI vendor copy 的 `pyproject.toml` 将固定 Git sources 替换为对应 remote vendor paths：LeRobot 对应 commit `0cf864870cf29f4738d3ade893e6fd13fbd7cdb5`，dlimp 对应 commit `ad72ce3a9b414db2185bc0b38461d4101a65477a`。随后 lockfile 已重新生成。

## 已完成的运行时同步与验证

- 已以 `uv sync --active --no-dev --locked` 安装 202 个运行时包；开发工具组未安装。
- 所有 uv cache 位于 `/root/shared-nvme/openpi-robot-runtime/uv-cache`，环境位于独立 `openpi-runtime`。
- 验证结果：`import openpi` 成功；JAX `0.5.3` 检测到 `CudaDevice(id=0)`；Torch `2.7.1+cu126` 检测到 NVIDIA RTX 4090。
- 当前没有 OpenPI checkpoint，没有加载 policy，也没有执行 GPU inference。

下一步必须单独评估 checkpoint 的下载源、准确大小、共享盘剩余空间和短时 GPU smoke test 预算。
