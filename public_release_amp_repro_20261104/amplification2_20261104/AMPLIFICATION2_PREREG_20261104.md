# 第二次加码预注册：安装报文网关定时丢弃诱发条件 C（Amplification-2 Pre-registration）

- **声明（多重检验）**：第一次确认（`AMPLIFICATION_CONFIRM_REPORT_20261104` / `AMPLIFICATION_PREREG_20261103`）**未达标**——Joint 下 E1 锁死 **0/96**（Wilson 95% CI 0–3.85%），S1/S2/S3 全假。本次为**第 2 次尝试**；所有推断须披露 multiplicity；第一次 0/96 **必须**与本次主终点并列报告。探索性 p 值不作为达标依据。
- 注册时间：2026-11-04（America/Los_Angeles），**须在 manip_check 与 confirm 任何一次计分运行之前**完成本文件与 `results/amplification2_<stage>_registration.json` 冻结。
- 代码位置（box）：`/workspace/wsn_ablation/repo/control_budget_study_20261015/`
- 冻结方式：`PYTHONPATH=engine python3 run_amplification2.py --stage <stage> --register-only` 生成登记 JSON（含全部配置与源/原生 SHA256）。正式运行若漂移则断言失败。
- 运行时 LLM 调用：0。不伪造、不按结果替换单元/臂/阈值；禁止看过结果后追加单元。

## 0. 为何改机制假设（相对第一次）

第一次用 **S1_overload_R0**（overload + 注册三中继故障）并按 **d(4,0)≥54 m** 选布局，指望“弱控制末跳 → 安装丢失 → F_s 盲锁死”。开发布局 pilot 曾有锁死，**新布局确认 0/96**，显示配方对开发集过拟合；几何假设 H2 不成立。

机制事实（仍成立，但诱发方式必须改）：
1. 安装确认**不是**独立 ACK，而是源在安装后以**新 version** 报到被网关推断（`BoundedInstallation.observe`）。
2. 安装下发走固定控制路由 9→5→4→源（`SendInstall`）；与数据路径无关。
3. 命题 T ∧ 无合格 F_s ⇒ 门关闭：无确认退出后，settled service 为 `installation_unconfirmed`（服务未知），故 `positive_recovery_evidence` **只能**靠 F_s 打开门；Joint 不清空 installation 对象。
4. 永久 `brokenInstall`（改走不可达 9→7→源）会使 **post_exit 之后的新安装同样失败**，无法检验 S2——故不用。

**本次改法**：在网关 `SendInstall` 处按**仿真时钟**定向丢弃安装报文（`install_dropped`），制造「已发安装意图 / 控制器已记账，但源未收到 → 无 version 确认」；丢弃窗口结束后恢复正常投递，使 post_exit 有机会真正打开并下发成功安装。诱发过程**不依赖** d(4,0)、不依赖 overload+R0 几何压力。

## 1. 选定诱发操纵（主配方 M1）

| 字段 | 冻结值 |
|---|---|
| 名称 | `M1_drop_both_0_200_dn36` |
| `dropInstallStartSec` | 0 |
| `dropInstallEndSec` | 200 |
| `dropInstallMask` | 3（源 0 与源 1） |
| scenario | `multi_failure` |
| faults | `[[145,3],[225,6]]`（**仅**下游中继 3→6；保留源首跳 2；**不是**确认丢失原因，只作 S2 服务损伤背景；与第一次 overload+R0+按 d(4,0) 选布局脱钩） |
| 其余 | 10 节点、generation_stop 330 s、动作截止 320 s、local15_event、统一控制预算、证据保护、版本节律、FIFO、epoch 证书、报告重试、阈值/F_s/报文/驱动与第一次相同（原生驱动已增加上述 3 个 CLI，默认关闭等于旧行为） |

**一句话**：在 [0, 200) s 内网关丢弃发往双源的安装包（确认丢失的直接原因），从而与布局几何无关地制造无确认窗口；预注册拆除下游中继 3/6 仅作服务损伤背景；200 s 后恢复投递以便检验 post_exit。

**为何与几何脱钩**：确认丢失由网关时钟丢弃决定，不读节点坐标、不读 d(4,0)、不用 overload+控制路由压力选格；下游 3/6 故障表对所有确认布局一视同仁，不作几何筛选。

### 附录备选（不作为主确认配方；仅当 M1 操纵检查失败且新开第 3 次注册时考虑）

`M2_drop_src0_0_200_downstream`：mask=1（只丢源 0）+ faults `[[145,3],[225,6]]`（下游中继，保留源首跳 2）。意图：不对称无确认 + 可能的服务损伤；仍不按 d(4,0) 选布局。

## 2. 分层设计

### 层 A — 诱发臂有效性（manip_check）

**目标**：验证操纵是否稳定制造「无确认且无合格 F_s」窗口——**不是** A 档终点。

- 单元：4 个全新布局 `budget_10_{2026110401..404}` × 2 输入种子 `2026110601..602` = **8 Joint 格**；另跑同格 `post_exit` 作恢复烟雾（共 16 次运行）。布局/种子均未出现在第一次 confirm、开发 pilot。
- **层 A 成功（单格）**：Joint 上 (i) ≥1 次 `abandoned_unconfirmed` 且无 `late_confirmation`；(ii) protocol 中 ≥1 条 `install_dropped`；(iii) 首次无确认退出后、动作截止前，在 `reason=installation_unconfirmed` 的已评估准入上 **allowed 次数 = 0**（即无 F_s 解锁）。
- **放大规则（冻结）**：8 个 Joint 格中 **≥6 格（≥75%）** 达层 A → 允许进入 confirm，配方/阈值不再改。若 &lt;6/8：本注册内**停止**，不放大；若再改操纵须新开第 3 次预注册并披露。
- 分析脚本：`analyze_amplification2_manip.py`（与登记一并冻结）。

### 层 B — 锁死终点与 A 档（confirm）

仅当层 A 放大规则满足后执行。成功定义与第一次**同一 E1 / opened / S1–S3**（`analyze_amplification_confirm.py` 逻辑；路径前缀 `amplification2_confirm`）。

- 布局：`2026110410..417`（8 个，全新，非 manip_check、非 amp1）。
- 输入：`2026110611..616`（6 个）。
- 单元：8×6=**48 单元**；每单元 8 臂 → **384 次**闭环（小于第一次 768，因操纵更强、预期发生率更高；仍要求独立布局覆盖）。
- 臂：与第一次相同（joint / post_exit / sham_release / wait_extend / fs_relax_scoped / thresh_relax_scoped / fs_relax_global / thresh_relax_global）。

**A 档阈值（不变）**：
- **S1**：Joint 下 E1 锁死单元 ≥3，且覆盖 ≥2 布局。
- **S2**：上述锁死单元中，post_exit opened ≥2（opened：退出后 ≥1 次授权、≥1 次安装，最差源服务相对 Joint ≥+1.0 pp；post_exit 另要求首次退出时刻与 Joint 相同）。
- **S3**：S2 成功格上，至少一个竞争臂（wait_extend 或 thresh_relax_scoped）不 opened；且 sham_release 在全部 confirm 单元与 Joint 逐位相同。
- 达到 A ⇔ S1 ∧ S2 ∧ S3（S4 写作约束：条件化边界，不写成更好协议）。

## 3. 停止规则

1. manip_check：16 次一次跑完（或不含 limit 的登记全集）；不因早期结果改 mask/窗口。
2. 层 A 不达标：停止，不进入 confirm；报告操纵失败。
3. confirm：384 次一次跑完；不提前停、不追加单元/输入；崩溃保留 `FAILED_ATTEMPT.txt` 同配置重跑并记入报告。
4. 审计失败的运行保留；含失败运行的单元不计入 S1–S3 分子。
5. 若 S1 不满足：**停止冲 A**；定稿为罕见病理 + **双阴性确认**（第一次几何配方 0/96 + 第二次直接丢弃诱发未达锁死阈值），档位停在边缘可投或改投负结果栏目。
6. 若 S1 满足而 S2/S3 不满足：报告「可诱发锁死，但 T 特异性未复现」。
7. **禁止**在看过任何计分结果后修改本预注册的操纵参数、单元列表或阈值。

## 4. 与第一次并列报告（正文/补充必登）

| 尝试 | 预注册 | 诱发 | Joint E1 | S1 | S2 | S3 |
|---|---|---|---|---|---|---|
| 1 | AMPLIFICATION_PREREG_20261103 | S1_overload_R0 + d(4,0) 分层 | **0/96** | 否 | 否 | 否 |
| 2（本注册） | AMPLIFICATION2_PREREG_20261104 | M1_drop_both_0_200_dn36（丢弃+下游3/6 共干预） | （确认后填） | （填） | （填） | （填） |

多重检验：两次主终点均披露；不以探索性对比或 manip_check 发生率替代 S1。

## 5. 数据可用性

公开：本预注册、`amplification2_*_registration.json`、冻结分析脚本与源文件 SHA256、原生 `wsn-closed-loop.cc` SHA256、汇总 JSON、protocol 中 `install_dropped` 计数。不公开伪造或筛选后的子集冒充全表。

## 6. 主张边界（S4）

即使达 A：主张仍为**条件化确认契约病理边界**（T ∧ ¬F_s 下可持久锁死；只放宽 T 可重开），**不是**提出更好路由/传输协议。须写明诱发为**受控网关丢弃**（外部操纵），外推到「自然无线丢失」时保持审慎，并并列第一次自然压力配方的阴性。

## 7. 风险与需拍板点（注册时已知）

1. **E1 严格性**：E1 要求末次无确认退出后、截止前**每一次**已评估准入的 settled reason 均为 `installation_unconfirmed`。短暂 `missing_fresh_source` 也会判非锁死（烟雾已见 1/28 步）。层 A 不要求 E1；S1 仍用冻结 E1。
2. **服务增益 / F_s 张力**：下游 3/6 旨在降低锁死期服务以便 S2；若源侧 F_s 因此合格，门会被打开、E1 失败。该张力事先承认；不在看结果后改故障表。
3. **窗口长度**：end=200 留 ≥120 s 给 post_exit 恢复；不因烟雾改窗口（除非新开注册）。
4. **原生侵入**：改 `SendInstall`（小改 + CLI），protocol 记 `install_dropped`；避免观测层造假。
5. **若第二次仍 0 锁死**：停止冲 A（见停止规则 5）。

## 附录 A：confirm 启动前披露补丁（2026-11-04，不计分改判）

本附录**不**修改第 1–3 节的配方 M1、E1、S1–S3、单元/臂列表或停止规则；仅记录 confirm 计分跑之前已发生的过程事实与披露义务。

1. **层 A 状态（confirm 前）**：`manip_check` 已完成；Joint 层 A **8/8** 达标，放大规则满足。manip_check 上探索性严格 E1 发生率为 **2/8**，非锁死格可见 `missing_fresh_source`（MFS）与 `installation_unconfirmed`（IU）混入——**不得**据此反写 E1 成功定义、放宽 IU-only、或改动 confirm 样本量/单元列表。E1 仍坚持：**仅**全程 IU（IU-only）。
2. **登记先于计分**：confirm 阶段必须先执行 `python3 run_amplification2.py --stage confirm --register-only`，生成并冻结 `results/amplification2_confirm_registration.json`（含全部 384 配置与源/原生/本预注册文件 SHA256），**之后**才允许首次计分运行。登记文件的 mtime 与 SHA256 须写入确认报告，以备审稿核对「先登记后跑」。
3. **共干预披露**：主配方 `M1_drop_both_0_200_dn36` 将网关安装丢弃（`dropInstall*`）与 faults `[[145,3],[225,6]]` **联合施加**。S1/S2/S3 是在「丢弃安装 + 下游中继拆除」联合条件下估计的；**不得**写成「纯丢弃安装」的边际效应。丢弃仍是确认丢失的直接机制；下游拆除为预注册的服务损伤背景。
4. **S4 / 方法边界**：诱发为**受控网关丢弃**（外部操纵），外推到自然无线丢失须审慎；正文/补充须与第一次确认 Joint E1 **0/96** 并列报告（多重检验）。
