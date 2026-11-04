"""Structure templates for group-meeting-deck (`deck.py init`). A template fixes what the meeting needs
to hear, not how it looks. Every [[placeholder]] is reported by `deck.py check` until it is replaced."""
from __future__ import annotations

TEMPLATES = {
    "progress": {
        "label": "Weekly progress update",
        "use": "Regular group meeting: what was planned, what was done, what failed, what you need.",
        "en": """---
title: [[Project name]]: progress update
presenter: [[Your name]]
group: [[Group / lab name]]
date: [[YYYY-MM-DD]]
style: clean
minutes: {minutes}
qa: {qa}
since: [[date of the previous update, YYYY-MM-DD]]
source: [[results files, notebook or manuscript the numbers come from]]
ledger: [[research/LEDGER.md, optional]]
---

## Where things stand
> [[One sentence: what is established now, and what is not]]

- Goal: [[the research question, one line]]
- Since last time: [[the one change that matters most]]

???
[[What to say in 30-45 seconds.]]

## Last time's plan, and what happened
- {{done}} [[planned item 1]]
- {{in-progress}} [[planned item 2: what is left]]
- {{blocked}} [[planned item 3: what blocked it]]

???
[[Go through each item; do not skip the ones that did not happen.]]

## [[Result 1, stated as a claim]]
![[[What the figure shows, with n, seeds or conditions]]]([[figures/result1.png]])

- {{preliminary}} [[the number, exactly as in the source, with its comparator]]

???
[[How the result was obtained; what would change your mind.]]

## What did not work
- {{negative}} [[route or experiment]]: [[what was observed, with the evidence]]
- {{blocked}} [[technical blocker; this is not evidence against the idea]]

???
[[Negative results and blockers belong in the meeting; say what you learned.]]

## Questions for the group
1. [[A decision or advice you need]]
2. [[A specific technical question]]

???
[[Leave room for discussion here.]]

## Plan until next meeting
- {{planned}} [[next step 1, with the criterion that would count as success]]
- {{planned}} [[next step 2]]

# Backup

## [[Backup: details people may ask about]] {{backup}}
- [[setup, parameters, extra figures]]
""",
        "zh": """---
title: [[项目名称]]：进展汇报
presenter: [[姓名]]
group: [[课题组]]
date: [[YYYY-MM-DD]]
style: clean
minutes: {minutes}
qa: {qa}
since: [[上次汇报日期 YYYY-MM-DD]]
source: [[数字所依据的结果文件、记录或稿件]]
ledger: [[research/LEDGER.md，可选]]
---

## 当前状态
> [[一句话：现在确立了什么，还没有确立什么]]

- 目标：[[研究问题，一行]]
- 本周期最重要的变化：[[一项]]

???
[[30–45 秒要讲的内容。]]

## 上次的计划与完成情况
- {{done}} [[计划项 1]]
- {{in-progress}} [[计划项 2：还剩什么]]
- {{blocked}} [[计划项 3：被什么卡住]]

???
[[逐项说明；没完成的也要讲。]]

## [[结果 1，用一句结论表述]]
![[[图中显示什么，样本量、种子或条件]]]([[figures/result1.png]])

- {{preliminary}} [[数字照抄来源，并写明对照]]

???
[[结果如何得到；什么情况会推翻它。]]

## 没有成功的尝试
- {{negative}} [[路线或实验]]：[[观察到什么，证据在哪]]
- {{blocked}} [[技术障碍；这不是否定该想法的证据]]

???
[[负面结果和障碍应当在组会上讲；说明学到了什么。]]

## 需要大家帮助的问题
1. [[需要的决定或建议]]
2. [[具体的技术问题]]

???
[[这里留出讨论时间。]]

## 下次组会前的计划
- {{planned}} [[下一步 1，以及判定成功的标准]]
- {{planned}} [[下一步 2]]

# 备用

## [[备用：可能被问到的细节]] {{backup}}
- [[设置、参数、补充图]]
""",
    },
    "journal-club": {
        "label": "Journal club / paper reading",
        "use": "Presenting someone else's paper: what it claims, how strong the evidence is, what it means for us.",
        "en": """---
title: [[Paper title]]
subtitle: [[First author et al., Venue Year; DOI]]
presenter: [[Your name]]
group: [[Group / lab name]]
date: [[YYYY-MM-DD]]
style: clean
minutes: {minutes}
qa: {qa}
source: [[the paper's PDF or text, so every number can be traced]]
---

## The question
- [[What problem the paper addresses, in our group's terms]]
- [[Why it matters now]]

???
[[One minute.]]

## What they claim
> [[The main claim, in the paper's own strength: proved / shown / suggested]]

- [[Headline number with its comparator, exactly as in the paper]]

## How they did it
- [[Key idea, method or design]]
- [[Data, model, sample or setting]]

## Main evidence
![[[Fig. N from the paper: what it shows]]]([[figures/paper_figN.png]])

???
[[Credit the figure to the paper on the slide.]]

## How strong is the evidence?
- Strengths: [[...]]
- Weaknesses or open questions: [[...]]
- Could we reproduce it? [[code, data, details available?]]

## What it means for our work
- [[Concrete consequence, idea or risk for our projects]]

## Discussion
1. [[Question for the group]]
2. [[Question for the group]]
""",
        "zh": """---
title: [[论文标题]]
subtitle: [[第一作者 等，期刊/会议 年份；DOI]]
presenter: [[姓名]]
group: [[课题组]]
date: [[YYYY-MM-DD]]
style: clean
minutes: {minutes}
qa: {qa}
source: [[论文 PDF 或文本，用于追溯每个数字]]
---

## 研究问题
- [[论文解决什么问题，用我们组的语言说]]
- [[为什么现在重要]]

???
[[一分钟。]]

## 论文的主张
> [[主要结论，保持原文强度：证明 / 显示 / 提示]]

- [[关键数字及其对照，照抄原文]]

## 方法
- [[核心思路、方法或设计]]
- [[数据、模型、样本或场景]]

## 主要证据
![[[论文图 N：显示了什么]]]([[figures/paper_figN.png]])

???
[[在幻灯片上注明图片出处。]]

## 证据有多强？
- 优点：[[...]]
- 不足或疑问：[[...]]
- 能否复现？[[代码、数据、细节是否公开]]

## 对我们工作的意义
- [[对我们项目的具体影响、想法或风险]]

## 讨论
1. [[给大家的问题]]
2. [[给大家的问题]]
""",
    },
    "proposal": {
        "label": "Project proposal / idea pitch",
        "use": "Asking the group for feedback or resources on a new direction before investing in it.",
        "en": """---
title: [[Proposal title]]
presenter: [[Your name]]
group: [[Group / lab name]]
date: [[YYYY-MM-DD]]
style: minimal
minutes: {minutes}
qa: {qa}
---

## The question
> [[One sentence a newcomer can follow]]

## Why now
- [[What changed: new data, method, result or need]]

## What is already known
- [[Closest prior work, with references; result of a novelty scout if run]]

## The idea
- [[What you would do differently]]

## How we will know it works
- [[A falsifiable criterion and a cheap pilot]]
- [[What result would make us stop]]

## Cost and risks
- [[Time, compute, money, people]]
- [[Main risk and fallback]]

## What I need from the group
1. [[Decision, resource or advice]]
""",
        "zh": """---
title: [[提案标题]]
presenter: [[姓名]]
group: [[课题组]]
date: [[YYYY-MM-DD]]
style: minimal
minutes: {minutes}
qa: {qa}
---

## 研究问题
> [[一句新同学也能听懂的话]]

## 为什么是现在
- [[发生了什么变化：新数据、新方法、新结果或新需求]]

## 已有工作
- [[最相近的已有工作及文献；如做过新颖性侦察，写结论]]

## 想法
- [[与已有做法的不同之处]]

## 如何判断它可行
- [[可证伪的判据与低成本预实验]]
- [[出现什么结果就停止]]

## 成本与风险
- [[时间、算力、经费、人力]]
- [[主要风险与备选方案]]

## 需要组里提供什么
1. [[决定、资源或建议]]
""",
    },
    "deep-dive": {
        "label": "Result deep-dive",
        "use": "One result examined in depth: setup, evidence, robustness, and what could make it wrong.",
        "en": """---
title: [[The result, as one claim]]
presenter: [[Your name]]
group: [[Group / lab name]]
date: [[YYYY-MM-DD]]
style: assertion
minutes: {minutes}
qa: {qa}
source: [[results files or manuscript]]
ledger: [[research/LEDGER.md, optional]]
---

## [[Claim, as a full sentence]]
![[[Main evidence: what is plotted, n and conditions]]]([[figures/main.png]])

## [[How the result was obtained]]
- [[Setup, data, parameters]]
- [[What was held fixed; what was varied]]

## [[The result holds under these checks]]
| Check | Result | Evidence |
|---|---|---|
| [[seeds / replicates]] | [[...]] | [[file]] |
| [[ablation / control]] | [[...]] | [[file]] |

## [[What could make it wrong]]
- [[Alternative explanation, and how it was ruled out or not]]
- {{unverified}} [[What has not been checked independently]]

## Next steps
- {{planned}} [[...]]
""",
        "zh": """---
title: [[结论，一句话]]
presenter: [[姓名]]
group: [[课题组]]
date: [[YYYY-MM-DD]]
style: assertion
minutes: {minutes}
qa: {qa}
source: [[结果文件或稿件]]
ledger: [[research/LEDGER.md，可选]]
---

## [[完整句子形式的结论]]
![[[主要证据：画的是什么，样本量与条件]]]([[figures/main.png]])

## [[结果是如何得到的]]
- [[设置、数据、参数]]
- [[固定了什么，改变了什么]]

## [[以下检验下结论仍成立]]
| 检验 | 结果 | 证据 |
|---|---|---|
| [[种子 / 重复]] | [[...]] | [[文件]] |
| [[消融 / 对照]] | [[...]] | [[文件]] |

## [[什么可能推翻它]]
- [[其他解释，以及是否已排除]]
- {{unverified}} [[尚未独立核查的部分]]

## 下一步
- {{planned}} [[...]]
""",
    },
    "rehearsal": {
        "label": "Talk rehearsal (conference, defense, job talk)",
        "use": "A practice run of an external talk in the group; timing is counted strictly.",
        "en": """---
title: [[Talk title]]
presenter: [[Your name]]
group: [[Affiliation]]
date: [[YYYY-MM-DD]]
venue: [[Conference / event]]
style: metropolis
minutes: {minutes}
qa: {qa}
source: [[the paper the talk is based on]]
---

## [[Motivation: the problem in one sentence]]
- [[Why the audience should care]]

## [[Main result, stated once, with its conditions]]
> [[Headline claim at the paper's strength]]

## [[Key idea]]
- [[...]]

## [[Evidence]]
![[[...]]]([[figures/fig2.png]])

## [[Limitations and outlook]]
- [[...]]

## Summary
1. [[Take-home message 1]]
2. [[Take-home message 2]]
""",
        "zh": """---
title: [[报告题目]]
presenter: [[姓名]]
group: [[单位]]
date: [[YYYY-MM-DD]]
venue: [[会议 / 场合]]
style: metropolis
minutes: {minutes}
qa: {qa}
source: [[报告依据的论文]]
---

## [[动机：一句话说清问题]]
- [[听众为什么要关心]]

## [[主要结果，连同条件只说一次]]
> [[按论文强度表述的核心结论]]

## [[核心思路]]
- [[...]]

## [[证据]]
![[[...]]]([[figures/fig2.png]])

## [[局限与展望]]
- [[...]]

## 总结
1. [[要点 1]]
2. [[要点 2]]
""",
    },
}
