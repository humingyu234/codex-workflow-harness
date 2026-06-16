# Codex Harness 工作流直观解释

这个项目不是要替代 Codex 或 Claude Code。

新版定位更清楚：

```text
Codex / Claude Code 负责计划、探索、写代码、调试、循环修复。
codex-harness 负责边界、证据、过期检测、review 输入、proof 和交接。
```

也就是说，harness 不是坐进驾驶位抢方向盘，而是在赛道边上做边界、
计时、验车和交接记录。

## 为什么不是控制 Codex，而是最大化 Codex

Codex 和 Claude Code 已经有很强的能力：

```text
plan mode
agent loop
hooks
subagents
resume
automation
```

所以第一版不应该重造这些能力。我们要做的是让模型放心发挥，同时保证：

```text
任务边界清楚
测试证据真实
旧证据不会冒充当前证据
reviewer 看到的是干净输入
最终交付能被别人复核
新 session 可以接上
```

## 文档和 CLI 各自负责什么

文档负责告诉模型应该怎么工作：

```text
AGENTS.md        短入口规则
docs/roadmap.md 方向和后续阶段
templates/      spec / plan / phase / review / proof 的稳定格式
recipes/        后续沉淀不同任务类型的做法
```

CLI 负责那些不能只靠模型自觉的检查：

```text
task start      记录 contract 和 baseline
task verify     检查 diff、边界和 required checks
stale detection 判断旧 verify/review 是否还能用
review-brief    给独立 reviewer 干净输入
proof-pack      汇总交付证据
resume-brief    给新 session 接力
```

直观理解：

```text
文档 = 操作说明和流程模板
CLI  = 体检仪、验收表和证据柜
```

## 为什么先做 evidence，再做 review/proof

如果测试证据不硬，后面的 review 和 proof 都会变软。

所以后续顺序是：

```text
1. 先增强 required_checks 证据
2. 再绑定 source_state 并检测 stale
3. 再生成 review-brief 和记录 review-result
4. 最后生成 proof-pack 和 resume-brief
```

你可以把它想成：

```text
先确认体检真的做了
再确认体检报告没有过期
再把报告交给医生复查
最后给出可交付证明
```

## 大型任务怎么跑

一个大任务不要让模型一口气全做完，而是这样：

```text
1. Codex 先读 AGENTS.md 和项目 profile，进入计划模式
2. 产出 spec、plan、phases
3. 用 codex-harness task start 记录 contract 和 baseline
4. Codex 只实现当前 phase
5. codex-harness task verify 检查边界和证据
6. 生成 review-brief，交给 fresh reviewer
7. 只修 P0/P1，再重新 verify
8. 生成 proof-pack 和 resume-brief
```

模型是主力工程师，harness 是施工记录、验收清单和交接包。

## 为什么不做复杂运行时

第一版刻意不做：

```text
多 agent runtime
LangGraph 编排
自动修复循环
复杂记忆数据库
dashboard
```

因为现在最需要的是：

```text
顺滑
稳定
少 bug
可复用
能提高真实开发质量
```

不是再造一个容易卡住的复杂系统。
