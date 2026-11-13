# 加码实验预注册：人工诱发条件 C + 竞争/安慰剂消融（Amplification Pre-registration）

- 注册时间：2026-11-03 23:30 PST（America/Los_Angeles），**确认阶段（confirm）任何一次运行之前**。
- 代码位置（box）：`raw_on_request/control_budget_study_20261015/`
- 冻结方式：运行 `python3 run_amplification.py --stage confirm --register-only` 生成 `results/amplification_confirm_registration.json`，其中含全部 768 个配置与下列文件的 SHA256：`amplification_arms.py, amplification_stages.py, run_amplification.py, analyze_amplification.py, analyze_amplification_confirm.py, analyze_contract_ablation.py, audit_case.py, contract_ablation.py, horizon_controller.py, budget_controller.py, fast_native_run.py` 以及原生驱动 SHA。正式运行时若任何文件或配置漂移，脚本断言失败、拒绝运行。
- 运行时 LLM 调用：0。不伪造、不按结果替换单元/臂/阈值。

## 0. 已做过的开发性（pilot）工作——如实披露
确认阶段之前，仅在**开发布局**（2026101501、2026101521–23、2026110301–04，均已在此前研究中使用过）上只跑 Joint 臂，用于选择压力配方（只看 Joint 的锁死发生率，未看任何放宽臂的效果）：

| 阶段 | 内容 | Joint 锁死到截止（E1） |
|---|---|---|
| pilot | 7 种故障时序 × 5 布局 × {10,20} 节点 × 2 输入，multi_failure | 1/140（仅原 adverse 单元，R0） |
| pilot2 | 5 种配方（含控制路由中继 4/5 故障）× 8 布局 × {10,20} × 3 输入 × {multi_failure, overload} | R0+overload 3/48；R7 五故障 multi 2/48；其余 0 |
| pilot3 | 4 种 overload 配方 × 8 布局 × 10 节点 × 6 输入 | R0+overload 1/48；其余 0 |

另有一次实现等价检查（check 阶段）：在原 adverse 单元上跑全部 8 个臂，确认本模块的 `post_exit` 臂逐位复现既有消融（0.5929→0.7997，67812→69811 B）；同时已看到该单元上 `fs_relax_global`（0.7902）与 `thresh_relax_global`（0.7964）也抬高服务，`*_scoped` 版本与 `wait_extend`、`sham_release` 与 Joint 逐位相同。**这是确认前已知信息**，故把"同格不复制"的主判据放在 scoped 竞争臂与 wait_extend 上，并把 global 臂作为探索性次要结果（见第 4 节）。

开发阶段发现（用于机制假设，非确认证据）：
1. 安装报文走固定控制路由 9→5→4→源（原生驱动第 415 行），与数据路径无关；锁死单元均为"某源安装丢失 → 该源仍以旧版本报到（双源新鲜）→ 旧路径在源首跳下游断开，源侧失败计数 F_s 看不到丢包"。
2. 低负载 multi_failure 下几乎不产生无确认退出；overload 产生大量无确认退出，但多数被合格 F_s 或后续确认重新打开；只有 F_s 盲的格子形成严格锁死。
3. 杀控制中继 4/5 会让源报告也失联（原因变成 `missing_fresh_source`），门虽关闭但 T 不是可识别的绑定原因——严格 E1 不计入，这是正确的排除。
4. 锁死格的布局都有 d(4,0)≥54 m（控制末跳偏弱）；d(4,0)<54 m 的开发布局 0 锁死（证据很弱，故仅作次要假设 H2）。

## 1. 压力配方（stress recipe，冻结）
- **S1_overload_R0**：overload 业务负载（`arrivals` 速率 10/40/10 /s，原有场景定义不变）**叠加**已注册三中继永久移除时序 `[[65,2],[145,3],[225,6]]`。原 40 例研究中 overload 从不带故障、multi_failure 从不带过载；本配方首次把两者组合，作为"负载 + 晚期数据中继故障"压力。
- 其余全部不变：10 节点、generation_stop 330 s、动作截止 320 s、local15_event 报告、统一控制预算、证据保护、版本节律、FIFO、epoch 证书、报告重试、阈值、F_s 规则、报文格式、原生驱动。

## 2. 单元（全部为从未运行过的新布局/新输入）
- **弱控制末跳层（stress，12 布局）**：按序扫描布局种子 2026110305 起，**仅凭几何**取前 12 个 d(4,0)≥54 m 的种子：2026110306, 309, 310, 319, 324, 327, 328, 331, 334, 336, 338, 340。
- **对照层（contrast，4 布局）**：同扫描中前 4 个 d(4,0)<50 m：2026110307, 311, 318, 320。
- 输入种子：2026110501–2026110506（6 个）。
- 单元数：16 布局 × 6 输入 = **96 单元**；每单元 8 臂 → **768 次闭环运行**。

## 3. 臂定义（全部基于 HorizonController，相对 Joint 只改一条规则）
| 臂 | 角色 | 规则 |
|---|---|---|
| joint | 基线 | 已实现的全局确认契约（前提 T 成立） |
| post_exit | 处理 | 只放宽 T：安装等待无确认结束且无挂起反馈事务时释放事务（与既有 `contract_ablation.PostExitMixin` 相同） |
| sham_release | 安慰剂（理智检查） | 计算同一释放条件并记日志，但不释放；必须与 Joint 逐位相同，否则整轮无效 |
| wait_extend | 竞争假设（"等待太短"） | 安装确认等待 10 s→20 s；T 不变 |
| thresh_relax_scoped | 竞争放宽（服务谓词） | 仅在 T 阻塞窗口内（当前安装已无确认退出），最差源及时率阈值 0.80→0.95 |
| fs_relax_scoped | 机制一致性臂（第二合取项） | 仅在 T 阻塞窗口内，F_s 资格 n≥20 且失败比≥0.20 → n≥5 且≥0.10 |
| fs_relax_global | 探索性 | 同上但全程生效 |
| thresh_relax_global | 探索性 | 同上但全程生效 |

预先写明的机制预测（Proposition 1：T ∧ 无合格 F_s ⇒ 门关闭）：
- post_exit：在锁死格应重新授权并下发安装，最差源服务上升。
- sham_release、wait_extend、thresh_relax_scoped：在锁死格**不应**打开门（T 阻塞期服务不可知，阈值无从作用；确认报文丢失不随等待时长恢复）。
- fs_relax_scoped：攻击第二合取项，**若**放宽后的 F_s 被触发则可能打开门——这不是安慰剂，是对"锁死=合取"的一致性检验；不计入通过/失败。
- global 臂：会改变退出前轨迹，可能经"避开 C"而非"打开 C"提升服务；仅探索性报告。

## 4. 端点与判据（`analyze_amplification_confirm.py`，冻结）
- **E1 锁死到截止**（与论文 I3 / `analyze_contract_ablation.post_exit` 完全一致）：最后一次无确认退出之后、动作截止前的每次被评估的准入检查，其服务原因均为 `installation_unconfirmed`，且不再下发安装。
- **门重新可达且同向效应（opened）**：某臂在首次无确认退出后至少 1 次准入被授权、且至少 1 次安装下发，且最差源服务相对同格 Joint ≥ +1.0 pp。对 post_exit 另要求首次退出时刻与 Joint 相同（释放前轨迹一致）。

**A 档证据阈值（贡献度专家给定，原样预注册）：**
- **S1**：Joint 下 E1 锁死单元 ≥3，且覆盖 ≥2 个布局。
- **S2**：上述锁死单元中，post_exit opened 的单元 ≥2。
- **S3**：在 S2 成功的每个单元上，至少一个竞争臂（wait_extend 或 thresh_relax_scoped）均**不** opened；且 sham_release 在全部 96 单元与 Joint 逐位相同。
- **S4**：主张仍为条件化边界（不写成更好协议）——写作约束，不由数据判定。
- 达到 A 档 ⇔ S1 ∧ S2 ∧ S3（S4 写作时执行）。

次要/探索性（不影响 A 档判定）：
- H2：弱控制末跳层锁死发生率 > 对照层（单侧 Fisher 精确检验）；总体发生率 + Wilson 95% CI。
- 非锁死单元上各臂的副作用：改变格数、升/降格数、平均 Δ服务（pp）、平均 Δ控制字节（%）。
- fs_relax_scoped 与 global 臂在锁死格的行为。

## 5. 停止规则
- 768 次运行一次跑完，不提前停止、不追加单元或输入、不重跑（除非进程崩溃；崩溃保留 `FAILED_ATTEMPT.txt` 并用同一配置重跑，记入报告）。
- 任一原生审计失败的运行保留并报告；含失败运行的单元不计入 S1–S3 的分子。
- 若 S1 不满足：如实报告"未达标"，本注册内不再加单元；任何后续加码须新开注册文件并标明是第二次尝试（多重检验风险在报告中写明）。
- 若 S1 满足而 S2 或 S3 不满足：如实报告"条件 C 可诱发，但 T 的因果特异性未在独立格复现"。
