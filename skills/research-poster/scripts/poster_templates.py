"""Structure templates for research-poster (`poster.py init`). Every [[placeholder]] is reported by
`poster.py check` until it is replaced."""
from __future__ import annotations

TEMPLATES = {
    "empirical": {
        "label": "Empirical study (question, methods, results, conclusions)",
        "en": """---
title: [[Title: the finding or the question, at most two lines]]
authors: [[A. Author¹, B. Author²]]
affiliations: [[¹University X · ²Institute Y]]
contact: [[email · project or paper URL]]
venue: [[Conference, city, year; poster number]]
size: {size}
style: classic
takeaway: [[One plain-language sentence: the main finding, at the strength the paper supports]]
logos: [[logos/university.png]]
qr: [[figures/qr-paper.png]]
source: [[manuscript, results files]]
---

## Question
- [[What is not known, in one or two lines]]
- [[Why it matters]]

## Approach
![[[Design or pipeline at a glance]]]([[figures/design.png]])
- [[Data / participants / material; n]]
- [[Key method]]

## Result 1: [[stated as a finding]]
![[[What is plotted; n; error bars]]]([[figures/result1.png]])

## Result 2: [[stated as a finding]]
![[[...]]]([[figures/result2.png]])

## Conclusions
1. [[Main conclusion, with its condition]]
2. [[Second conclusion]]
- Limitation: [[the one a visitor will ask about]]

## References {{footer}}
[[1. Author, Title, Venue (Year). 2. ...]]
""",
        "zh": """---
title: [[题目：结论或问题，至多两行]]
authors: [[作者甲¹，作者乙²]]
affiliations: [[¹某大学 · ²某研究所]]
contact: [[邮箱 · 项目或论文链接]]
venue: [[会议，城市，年份；展板编号]]
size: {size}
style: classic
takeaway: [[一句通俗的话：主要发现，强度与论文一致]]
logos: [[logos/university.png]]
qr: [[figures/qr-paper.png]]
source: [[稿件、结果文件]]
---

## 研究问题
- [[尚不清楚的是什么，一两行]]
- [[为什么重要]]

## 方法
![[[设计或流程示意]]]([[figures/design.png]])
- [[数据 / 被试 / 材料；样本量]]
- [[关键方法]]

## 结果一：[[用结论表述]]
![[[画的是什么；样本量；误差棒含义]]]([[figures/result1.png]])

## 结果二：[[用结论表述]]
![[[...]]]([[figures/result2.png]])

## 结论
1. [[主要结论，连同其条件]]
2. [[次要结论]]
- 局限：[[观众最可能问的那一条]]

## 参考文献 {{footer}}
[[1. 作者，题目，期刊 (年份)。2. ...]]
""",
    },
    "theory": {
        "label": "Theory / mathematics (problem, main result, proof idea, consequences)",
        "en": """---
title: [[Title]]
authors: [[A. Author¹, B. Author²]]
affiliations: [[¹University X · ²Institute Y]]
contact: [[email · arXiv ID]]
venue: [[Conference, year]]
size: {size}
style: minimal
takeaway: [[The main theorem in words, with its assumptions]]
source: [[main.tex]]
---

## Problem
- [[Setting and the quantity of interest]]
- [[What was known: the previous best bound, with reference]]

## Main result
> [[Theorem: exact statement, all hypotheses]]

$$ [[the key formula]] $$

## Proof idea
1. [[Step 1]]
2. [[Step 2: the new ingredient]]
3. [[Step 3]]

## Consequences
- [[Corollary or application]]
- [[Where the bound is tight, or why it cannot be improved by this method]]

## Open questions
- [[...]]

## References {{footer}}
[[...]]
""",
        "zh": """---
title: [[题目]]
authors: [[作者甲¹，作者乙²]]
affiliations: [[¹某大学 · ²某研究所]]
contact: [[邮箱 · arXiv 编号]]
venue: [[会议，年份]]
size: {size}
style: minimal
takeaway: [[用文字表述主定理，连同假设]]
source: [[main.tex]]
---

## 问题
- [[设定与关心的量]]
- [[已知结果：此前最好的界及文献]]

## 主要结果
> [[定理：完整陈述，包括全部假设]]

$$ [[关键公式]] $$

## 证明思路
1. [[第一步]]
2. [[第二步：新的要素]]
3. [[第三步]]

## 推论
- [[推论或应用]]
- [[界在何处是紧的，或为何此方法无法改进]]

## 开放问题
- [[...]]

## 参考文献 {{footer}}
[[...]]
""",
    },
    "billboard": {
        "label": "Billboard (#betterposter): one finding in the centre",
        "en": """---
title: [[Formal title]]
authors: [[A. Author¹, B. Author²]]
affiliations: [[¹University X]]
contact: [[email]]
size: {size}
style: billboard
takeaway: [[The main finding in plain language, ==the key words== highlighted]]
qr: [[figures/qr-paper.png]]
source: [[manuscript]]
---

## Background {{col=1}}
- [[...]]

## Methods {{col=1}}
- [[...]]

## Key figure {{center}}
![[[...]]]([[figures/key.png]])

## More results {{col=2}}
![[[...]]]([[figures/extra.png]])

## Details {{col=2}}
- [[limitations, data, code]]

## References {{footer}}
[[...]]
""",
        "zh": """---
title: [[正式题目]]
authors: [[作者甲¹，作者乙²]]
affiliations: [[¹某大学]]
contact: [[邮箱]]
size: {size}
style: billboard
takeaway: [[用通俗语言说出主要发现，==关键词== 高亮]]
qr: [[figures/qr-paper.png]]
source: [[稿件]]
---

## 背景 {{col=1}}
- [[...]]

## 方法 {{col=1}}
- [[...]]

## 关键图 {{center}}
![[[...]]]([[figures/key.png]])

## 更多结果 {{col=2}}
![[[...]]]([[figures/extra.png]])

## 细节 {{col=2}}
- [[局限、数据、代码]]

## 参考文献 {{footer}}
[[...]]
""",
    },
}
