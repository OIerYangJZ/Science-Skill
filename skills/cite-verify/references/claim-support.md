# 论断支撑检查流程

## 1. 对每个"句子 + 引用"

1. **拆出论断。** 这句话把什么归于被引文献？写成一句可以核对的陈述，例如"[12] 证明了 X 在条件 C 下需要 Ω(n log n) 次查询"。
2. **定位原文。** 先读摘要；如果论断涉及具体定理、数字或条件，找到对应的定理或章节编号。原文来源依次为：arXiv 全文（`https://arxiv.org/abs/<id>`）、出版社开放获取页面、LibKey 或机构访问。WebFetch 返回的是模型改写过的文本，只能用来定位，不能用于逐字引用。
3. **判断。**

| 结论 | 标准 |
|---|---|
| 支撑 | 原文明确给出这个结论，条件一致或更宽 |
| 部分支撑 | 原文给出的结论更弱、条件更窄、只是数值证据或猜想，或者只在特殊情形下成立 |
| 不支撑 | 原文没有这个结论，或者结论相反，或者引错了文献（常见于同一作者的另一篇） |
| 无法核实 | 拿不到全文，摘要又不够判断 |

4. **写依据**：引用原文的相应位置（定理号或节号，加不超过 40 词的原文），给出建议的改写。

## 2. 常见错误模式

- **升级**：原文是猜想、启发式或数值观察，正文写成 "proved" 或 "showed"。
- **范围外推**：原文只针对某个模型或参数范围，正文写成普遍结论。
- **张冠李戴**：结论来自同组作者的另一篇文章，或来自被引文献所引用的文献。
- **过时**：后续工作已经改进或推翻了这个结果，正文仍说 "the best known"。这时用 novelty-audit 的 `citing` 命令查被引文献的后续工作。
- **综述代引**：引一篇综述来支撑一个具体的技术结论。应引原始文献。
- **自引误述**：自己以前的工作被描述得比实际更强。

## 3. 记录格式（`refcheck/<date>/claims.md`）

| key | 位置 | 正文句子（摘录） | 拆出的论断 | 原文依据（定理/节 + 摘录） | 结论 | 建议改写 |
|---|---|---|---|---|---|---|

## 4. 子代理分工提示（按引用键分组时使用）

```
You check whether cited sources support the sentences that cite them.
For each item below (key, sentence, location), open the source (arXiv or
publisher open-access page), find the specific result, and classify as:
supports / partially supports / does not support / cannot verify.
Quote at most 40 words of the source with its theorem/section number.
Do not rely on memory of the paper; if you cannot access the text, say so.
Answer in Chinese; quotes in English.
<items>
```
