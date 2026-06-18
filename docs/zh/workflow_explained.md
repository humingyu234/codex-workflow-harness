# Codex Harness 工作流直观解释

这份文档是中文解释版，帮助你快速理解 `codex-harness` 为什么这样设计。

## 一句话

```text
Codex / Claude Code 负责把活做出来。
codex-harness 负责证明这次活可信、可审、可交接。
```

它不是要控制 Codex，也不是要重造一个 agent runtime。它更像是开发过程旁边的验收台、证据柜和交接单。

## 文档和 CLI 各自负责什么

```text
文档：
告诉 Codex 和人应该按什么流程工作。

CLI：
记录真实证据，判断旧证据是否过期，生成 review/proof/handoff 需要的材料。
```

更直观一点：

```text
文档 = 操作说明和模板
CLI  = 体检仪、验收表、证据柜
```

所以不要把所有东西都写成代码，也不要只靠文档提醒。文档负责方向，CLI 负责不能靠记忆和自觉完成的检查。

## 为什么不是“限制 Codex”

Codex 和 Claude Code 已经很擅长：

```text
理解任务
探索代码
制定计划
写代码
调试
循环修复
使用子 agent 或工具
恢复会话
```

所以 harness 不应该抢这些工作。它要补的是 Codex 本身不会天然替你保存好的东西：

```text
任务边界
允许改哪些文件
不允许改哪些文件
required checks 的真实输出
当前代码状态
旧 verify/review 是否已经过期
独立 reviewer 应该看什么
最终交付证据在哪里
新 session 怎么接上
```

## 大任务怎么跑

大型任务不要一口气全做完。更稳的方式是：

```text
0. 新项目先用 project init 写 project-profile 和 recipes
1. 先把需求变成 spec
2. 再拆成 plan 和 phase
3. 用 task start 记录边界和 baseline
4. Codex 只做当前 phase
5. task verify 记录真实检查结果
6. review-brief 交给 fresh reviewer
7. 只修 P0/P1 问题
8. 最后生成 proof pack / resume brief
```

这套流程的重点不是“慢”，而是避免最后才发现方向错了、证据旧了、review 看错材料了。

如果只是想知道当前任务卡在哪一步，可以跑：

```bash
codex-harness task status
```

它不指挥 Codex 写代码，只根据已有事实告诉你：

```text
needs_verify
needs_reverify
needs_review
needs_review_refresh
needs_repair
ready_for_proof_pack
ready_for_delivery
```

## 为什么先做 evidence，再做 review/proof

如果测试和 source state 不可靠，后面的 review 和 proof 都会变软。

正确顺序是：

```text
先确认检查真的跑过
再确认检查对应的是当前代码
再把干净材料交给 reviewer
最后生成可以交付给人的 proof pack
```

这就是为什么前面几个 phase 先做：

```text
Verification Evidence
Source State + Stale Detection
Review Brief + Review Record
Proof Pack
```

## 每个文件大概是干什么的

```text
AGENTS.md
给 Codex 看的短入口规则。

docs/roadmap.md
写项目方向、后续 phase、哪些暂时不做。

docs/workflow.md
主流程说明。以后不知道怎么跑任务，先看它。

docs/task_modes.md
只负责判断任务该走 direct / checked / controlled / council。

docs/review_process.md
说明独立 reviewer 怎么审、怎么记录结论。

docs/proof_pack.md
说明最终交付证据包应该包含什么。

docs/templates/
spec、plan、phase、review、proof 的模板骨架。

.codex-harness/project-profile.md
某个具体项目自己的技术栈、路径、检查命令和保护路径。

.codex-harness/recipes/
不同任务类型的流程卡片，比如 bugfix、feature、refactor、take-home、open-source-pr。
```

## 暂时不做什么

第一版不要做这些：

```text
复杂多 agent runtime
LangGraph 编排
自动修复循环
大型 dashboard
复杂记忆数据库
后台调度系统
```

不是它们没价值，而是现在最重要的是让主路径顺滑、稳定、可信。先把证据、review、proof、resume 做稳，再考虑扩展。
