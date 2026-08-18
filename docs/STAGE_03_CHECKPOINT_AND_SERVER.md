# Stage 3 — π0.5-DROID Checkpoint and Official Policy Server

日期：2026-08-17
范围：下载官方 π0.5-DROID checkpoint，并在完成后进行短时 remote policy-server smoke test。

## 下载决策

- 模型：官方 `gs://openpi-assets/checkpoints/pi05_droid`。
- 精确对象总量：20 files，12,429,488,598 bytes（约 12.43 GB / 11.58 GiB）。
- 持久化位置：`/root/shared-nvme/openpi-robot-runtime/openpi-cache/openpi-assets/checkpoints/pi05_droid/`。
- 下载机制：OpenPI `download.maybe_download`，以 `.partial` 目录下载完成后原子移动；不写入容器系统盘。
- 资源前提：下载前 shared-nvme 可用约 36 GB；完成后仍预计保留约 23 GB。
- GPU：下载本身不加载模型、不消耗显存；GPU 使用只发生在后续模型 server load 与 client inference。

## 后续 smoke-test 范围

1. 验证 checkpoint 目录和共享盘余量。
2. 启动官方 `scripts/serve_policy.py policy:checkpoint --policy.config=pi05_droid`。
3. 用官方 simple client 发送一次 schema-correct mock DROID observation。
4. 记录 action chunk shape、server/model timing、显存占用和 client round-trip。
5. 结束 server，避免空闲计费。

不包含训练、微调、真实机器人控制或长时间 GPU 推理。

## 2026-08-18 — Project adapter and closed-loop software integration

### Checkpoint final integrity

- Official manifest result: 20/20 expected objects matched by relative path and
  exact byte size; total `12,429,488,598` bytes. The temporary
  `.openpi-download-partial` path no longer exists.
- Two extra busy `.nfs*` objects are not official checkpoint files. They were
  left untouched because their lifecycle must be diagnosed before any cleanup.

### Official server and project-client verification

1. `scripts/serve_policy.py --port 8000 policy:checkpoint
   --policy.config=pi05_droid --policy.dir=<checkpoint>` restored successfully
   and `/healthz` returned HTTP 200.
2. The official simple DROID client completed one schema-correct request. Its
   timing artifact records client 80.66 ms, server 79.52 ms, and policy 57.23 ms.
3. `OfficialOpenPIDroidClient` was then exercised against the same server. It
   received a validated horizon-15, action-dimension-8 response; project-side
   measurements were ~99.56 ms client round trip, 97.28 ms server inference,
   and 57.69 ms policy inference.
4. `StaticFrameOpenPIBridge` connected the real client to `ClosedLoopRuntime`.
   With `execution_horizon=1`, the integration smoke issued two fresh policy
   requests and executed two actions through adapter + safety + `MockDroidRobot`.
   Client round trips: 103.84/87.72 ms; server: 100.97/85.80 ms; policy:
   58.99/57.66 ms. The second request used the changed mock joint state.

Result artifact:
`/root/shared-nvme/openpi-robot-runtime/results/project_runtime_closed_loop_smoke.json`.
Remote log:
`/root/shared-nvme/openpi-robot-runtime/logs/project_runtime_closed_loop_smoke.log`.

### Scope and shutdown

- Test images were static zero `224x224x3` RGB frames; execution was strictly
  `MockDroidRobot`. No camera, simulator task, robot SDK, motor, or physical
  robot was connected.
- The policy server was stopped with SIGTERM after collection. Its ~20.9 GB GPU
  allocation was released; checkpoint and artifacts were retained.

## 2026-08-17 下载恢复记录

- 远端直接下载的实测速度约为 `0.7 MiB/s`；远端 `curl` 直连 GCS 的 1 MiB 测试仅约 `0.18 MiB/s`。
- 本地中转测速：Windows 从 GCS 约 `0.08 MiB/s`，Windows 上传至远端约 `1.02 MiB/s`；因此不采用本地下载后上传。
- 已停止会重传已有对象的 `gsutil rsync`，并清理其 `.gstmp` 临时文件。共享盘清理后约有 `31 GB` 可用空间。
- 现用脚本：`/root/shared-nvme/openpi-robot-runtime/scripts/download_missing_pi05_droid.py`。它按 GCS 元数据逐对象比较相对路径和精确字节数，只下载缺失对象；每个对象先写入同目录临时文件、校验大小后原子改名。
- 恢复时精确缺失：6 个大分片、`12,293,989,601 bytes`；14 个已完整小文件（约 `135 MB`）被跳过。按此前较快的远端 gcsfs 实测，保守预计约 5 小时；下载阶段不使用 GPU。

## 2026-08-17 网络诊断补充

- 当前限制位于 robot-cloud 到 Google Cloud Storage 的出口路径，不是 GPU、共享盘或 Windows 本机 VPN。远端 4 并发 1 MiB Range 请求总吞吐约 `0.185 MiB/s`，因此简单增加并发无效。
- 容器解析 Google 端点时优先得到 IPv6 地址；实测 IPv6 连接 GCS 失败。强制 IPv4 的 1 MiB 首段约 `0.33 MiB/s`，但 8 MiB 持续测试随后停滞，因此暂不将主下载器切换为 curl IPv4。
- 本机通过 `127.0.0.1:7897` 代理的 GCS 样本约 `0.13 MiB/s`，不优于可靠的远端直连；不采用本地中转或远端经本机代理的长期通道。
- 若要获得数量级提升，可信的外部选项是切换到 Google 出口质量更好的容器站点/实例，或使用模型发布方明确提供的镜像；当前官方文档仍指定 GCS checkpoint 路径。

## 2026-08-17 checkpoint 方案复核与空间审计

- 已停止极慢的受控下载，并保留当前 `.openpi-download-partial` 分片（约 697 MB）。不再将下载当作 GPU 工作；GPU 在此阶段保持空闲。
- 官方 `maybe_download` 只在最终正式目录存在时才视为缓存命中；它将目录下载至 `.partial`，再整体移动。其 `gsutil -m cp -r` 分支没有在 OpenPI 层面验证或承诺利用本项目遗留 `.partial` 的可靠续传。因此该分片应保留，但不能作为“官方可恢复断点”的承诺。
- 候选 `ankile/openpi-pi05-droid-pretrained` 是个人账户发布的 bfloat16 转换版，仓库约 5.25 GB；官方原始 checkpoint 为 12.43 GB，二者分片名不同，不能视为字节级或 dtype 完全一致的镜像。它宣称使用 `pi05_droid` 与 Orbax 格式，故可作为隔离 smoke-test 候选；只有下载后以当前 OpenPI runtime 成功加载并完成一次 schema-correct inference，才可确认运行时兼容。不得将其称为官方镜像或基线等价物。
- 当前容器到 Hugging Face 的 1 MiB 测试也停滞，尚未证明它能改善网络问题；未下载任何 HF 权重。
- 空间审计：shared-nvme 可用约 28 GB，已达到最低 25 GB 目标。Project 1 仅余 `/root/shared-nvme/results` 约 2.2 MB（GIF、MP4、图与 JSON），应保留。可再生成、且不影响已建环境的候选清理项为 Project 2 `uv-cache/archive-v0` 约 7.6 GB；其次是通用 `pip-cache/http-v2` 约 3.0 GB 与 `conda-pkgs` 约 2.3 GB。均未执行删除。

## 2026-08-17 受控续传恢复

- 用户确认继续下载后，启用 `scripts/resume_pi05_droid_ipv4.py`。该脚本使用 HTTPS Range 的 `curl -4 --continue-at -`，直接续写同目录 `.openpi-download-partial`，完成后校验精确字节数并原子改名。
- 已验证第一个大分片从 byte `696,668,189` 继续，未重新下载该部分。实时速度约 `50–56 KB/s`；以缺失总量估计约 3–4 天，网络波动会影响该区间。
- 下载仅使用网络、少量 CPU 和 shared-nvme I/O；不使用 RTX 4090。GPU 可以被其他任务使用，但在 checkpoint 完成后启动 policy server 前须停止或协调其他占用 GPU 的任务。

## 2026-08-17 网络中断恢复守护

- 已观察到一次真实失败：`curl` 退出码 56（`Recv failure: Connection reset by peer`）。断点文件被完整保留，原 downloader 会因此退出，不能以短时进程存在判断为持续健康。
- 经用户授权，新增独立 watchdog `scripts/watch_resume_pi05_droid.py`。它不修改原 downloader、checkpoint、cache 或 `.openpi-download-partial`；每 30 秒检查原续传脚本，只有在其异常退出时才用同一 `resume_pi05_droid_ipv4.py` 重新启动。
- 已验证 watchdog 启动后原 downloader 与 curl 保持运行，断点文件继续增长。恢复仍通过同一 HTTPS IPv4 Range `--continue-at -` 机制完成，而非从头下载。

## 2026-08-18 checkpoint 完整性确认

- `pi05_droid` 官方 GCS 清单的 20 个对象已全部存在；逐路径、逐精确字节数核验通过，总计 `12,429,488,598 bytes`，无 mismatch，`.openpi-download-partial` 已不存在。
- 当前目录另有两个不属于官方清单的 `.nfs*` 文件（约 2.41 GB 与 2.15 GB），它们来自先前中断/删除过程的 NFS 临时句柄，不属于 checkpoint。为避免破坏仍可能持有的文件句柄，本阶段未删除；后续需要先查明持有进程，再以用户授权的方式回收。
- watchdog 仍在运行；它发现 `QUEUE files=0` 后不再下载权重。正式启动 policy server 前应停止 watchdog，防止无意义的周期性元数据检查。

## 2026-08-18 官方 policy-server smoke test

- 使用当前独立环境、已验证 checkpoint 和官方命令启动 `scripts/serve_policy.py --port 8000 policy:checkpoint --policy.config=pi05_droid --policy.dir=<local-checkpoint>`。模型 checkpoint restore 约 19 秒；`/healthz` 返回 HTTP 200。
- 官方 `examples/simple_client/main.py --env DROID --host 127.0.0.1 --port 8000 --num-steps 1` 成功完成一次 schema-correct mock 请求；不连接真实机器人。
- 结果保存在 `/root/shared-nvme/openpi-robot-runtime/results/pi05_droid_official_smoke_timings.parquet`：client `80.66 ms`、server `79.52 ms`、policy `57.23 ms`、server previous-total `81.00 ms`。
- server 加载时 RTX 4090 占用约 `20.9 GB`，验证后已以 SIGTERM 优雅停止；checkpoint、日志和 timing artifact 均保留，GPU 已释放。
