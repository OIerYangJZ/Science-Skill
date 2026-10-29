# 模板

## 1. 审稿子代理提示词

```
You are an independent referee for <journal>, expert in <direction>. Your
specific responsibility: <one sentence, e.g. "verify the number-theoretic
proofs in Appendices F-J and the tube-count constants">.

Materials (read-only): <pack path>. The manuscript is <main.tex, supplement.tex>,
version pinned by SHA-256 in <PIN.json>; your line numbers refer to this version.
Journal criteria (verbatim): <criteria.txt>

Rules:
- Read only inside <pack path>. Do not open any other directory, in particular
  not the source repository, author notes, earlier reviews or cover letters.
- Run code only in your work copy <work-role path>. Record every command.
- Reproduce numbers where you can; say which you reproduced and which you did not.
- Be concrete: every major issue needs a location (file:line or theorem/figure),
  the evidence, and the change you request.
- Do not soften or inflate: state your confidence for each part.

Write your report to <reports/role.md> in <Chinese/English> with these sections:
1. Summary of the submission (what is claimed, in your own words)
2. Recommendation and confidence (accept / minor / major / reject / transfer;
   confidence per part: high / moderate / low)
3. Overall assessment: strengths; weaknesses relative to the journal criteria
4. Major issues (M1, M2, ...): claim, location, evidence, requested change
5. Minor issues (numbered)
6. Verification performed (files read, commands run, numbers reproduced with values)
7. Not checked (be explicit)
8. Files read (complete list)
```

## 2. 联合报告结构（`joint_report.md`）

```markdown
# <方向数>方向联合审稿与修订方案

日期：YYYY-MM-DD。本报告由 AI 模拟审稿生成，不代表真实审稿人或期刊决定。
锁定版本：main.tex SHA-256 `...`；supplement.tex `...`。行号仅适用于该版本。

## 1. 总体判断

<一段：建议的结论；最需要修复的是什么；哪些没有被推翻；哪些尚未独立认证>

| 审稿方向 | 独立判断 | 主要认可 | 主要修订要求 |
|---|---|---|---|

<各方向侧重点的差异；交叉讨论后的共识与分歧>

## 2. 优先修订的问题及其性质

| 优先级 | 问题与证据 | 判定范围 | 最小修复 |
|---|---|---|---|
| P0 | ... | 已核实的事实错误 / 主张超出已证范围 / ... | ... |

"P0"表示先修它全文主张才能一致，不一定意味着核心定理错误。"P1"也不应只当作文字润色处理。

## 3. 具体问题的处理建议
<按问题展开：可以直接采用的定义性文字、最小可核验的实例、需要补的证明步骤>

## 4. 本轮得到的具体改进（如有）
<例如更紧的数值界、补上的证明，附复算脚本>

## 5. 修订顺序

| 顺序 | 修改内容 | 完成标准 |
|---|---|---|

## 6. 验证记录与后续工作

本轮实际完成：...
本轮未完成：...（不能写成"已验证"）
复算命令：...
- [ ] 继续修稿前核对稿件哈希（`review_pack.py check-pin`）
- [ ] ...
```

## 3. 核实记录（`verification.md`）

```markdown
| # | 来源 | 声称的问题 | 核实动作 | 结果 | 依据 |
|---|---|---|---|---|---|
| 1 | methods M2 | 工具的精度参数用的是另一种距离 | 读所固定版本的源码；用仓库数据算"实测误差 ÷ 名义参数" | 成立 | 源码位置；比值约 0.5 |
| 2 | stats minor 1 | "其他参数最多给出 X"不对 | 在副本中做参数扫描 | 成立 | 扫描输出，最大值高于 X |
| 3 | theory M5 | 某常数的下限应更高 | 精确计数复算 | 部分成立 | 审稿人所给参数处的计数有误，结论实质成立 |
```

## 4. 编辑角色（可选）

直接使用 paper-polish 的 `references/blind-editor-test.md` 第 2 节，只给编辑标题、摘要、引言、图 1 图注，以及（可选的）cover letter。编辑的结论单独成节，不和审稿人的推荐意见合并。

## 5. 审稿方向菜单与报告规范

按论文类型挑 2–4 个方向。报告规范的清单要从官方来源抓取原文（EQUATOR Network: equator-network.org，或者各规范官网），不能凭记忆列条目。

| 论文类型 | 可选审稿方向 | 常用报告规范 |
|---|---|---|
| 理论 / 数学 | 证明正确性；与已有结果的关系；应用意义 | — |
| 随机对照试验 | 临床或领域专家；试验统计（样本量、主要终点、多重性、缺失数据）；伦理与注册 | CONSORT（含摘要扩展）、SPIRIT（方案） |
| 观察性研究 | 领域专家；流行病学与因果推断（混杂、选择偏倚、敏感性分析）；统计 | STROBE、RECORD（常规数据）、RECORD-PE |
| 诊断准确性 | 临床专家；诊断方法学 | STARD |
| 预测模型 | 领域专家；建模与验证（校准、外部验证、过拟合） | TRIPOD（含 TRIPOD+AI） |
| 动物实验 | 领域专家；实验设计与统计（随机化、盲法、样本量） | ARRIVE |
| 系统综述 / 元分析 | 领域专家；检索与偏倚风险；统计合并与异质性 | PRISMA、GRADE |
| 卫生经济学评价 | 卫生经济学方法；领域专家 | CHEERS |
| 定性研究 | 领域专家；定性方法（抽样、饱和、反身性） | SRQR、COREQ |
| 心理学 / 行为科学 | 领域专家；统计与可重复性（预注册、功效、多重比较） | APA JARS |
| 计算 / 机器学习 | 领域专家；方法与基线公平性；复现性（代码、数据、种子、数据泄漏、计算预算） | 目标会议的论文清单（如 NeurIPS paper checklist）、REFORMS |
| 计算模拟 / 数值方法 | 领域专家；数值方法与误差；复现性 | — |

审稿子代理的职责说明里，要写明"按 <规范> 清单（附后）逐条检查，标出缺失项及其在稿件中应在的位置"。
