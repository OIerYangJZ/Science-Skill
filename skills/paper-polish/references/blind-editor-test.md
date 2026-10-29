# 盲测：模拟编辑与过冲审查

两个子代理都必须**独立**：不给它们看 survey_report、polish_notes、ledger 或本对话的分析。审稿子代理一旦读了作者的笔记，判断就会被带偏。Case B 的做法是让审稿子代理不读联合报告，事后再由主会话逐条核实。

结论一律标为"推断"。

## 1. 准备材料

在 `polish/<date>/blind/` 下准备：

- `A.txt`、`B.txt`：原稿和新稿各一份，内容都是标题 + 摘要 + 引言 + 图 1 图注，转成纯文本或保留 LaTeX 均可。哪一份是新稿用随机方式决定，对应关系只记在 `blind/key.md` 里，不写进提示词。
- `criteria.txt`：池 C 中期刊编辑标准的原文摘录。
- 过冲审查要用的新稿全文路径：正文 + 附录，其中摘要和引言替换为新稿版本。如果没有合并，就把新的摘要和引言文件与原稿正文一起给它。

## 2. Editor test 提示词

用 Agent 工具，subagent_type 选 general-purpose。下面是提示词模板，尖括号里的内容要替换掉：

```
You are a handling editor at <journal>. You decide whether to send manuscripts
out for review. Editors at this journal apply these criteria (verbatim from the
journal's site):

<criteria.txt>

You have about five minutes per manuscript and read only what is below: title,
abstract, introduction, and the Fig. 1 caption. Two versions of the same
manuscript are in <path>/A.txt and <path>/B.txt. Read A first, write your
answers for A, then read B. Do not read any other file in the repository.

For each version, answer in Chinese (quote English text verbatim when you
cite it):
1. 用一句话说出这篇文章的主要新结果。如果读完仍说不出，就写"说不出"，并指出
   你在哪一句之后放弃寻找。
2. 为什么重要：它改变了什么，或约束了谁。
3. 你认为最接近的前人工作是什么，本文比它强在哪里。如果文中没有点名，就写
   "未点名"。
4. 送外审还是 desk reject？给出 1–3 条理由，并对照上面的期刊标准。
5. 你在哪几句话上卡住了（逐字引用），为什么。
6. 有没有让你觉得作者在过度防御或过度宣称的句子（逐字引用）。

Then compare: which version lets an editor find the contribution faster, and
why? Which sentences in the better version would you still change?
Return everything as markdown.
```

## 3. Overclaim referee 提示词

```
You are a careful referee for <journal> with expertise in <field>. Read the
manuscript at <path> (main text and appendices). The abstract and introduction
are in <new abstract/intro file>. Do not read any notes, reports or files
under polish/ other than this one.

Task: list every sentence in the title, abstract, introduction and conclusion
that claims more than the body supports. Include:
- conditional results stated without their condition;
- numerical or sampled evidence stated as proof;
- words such as law, universal, first, optimal, tight, orders of magnitude
  without a matching theorem or a named, non-strawman baseline;
- a claim about a broader class than the theorem covers;
- non-effective asymptotics presented as practically relevant.

For each: verbatim sentence, location, what the body actually supports (with
theorem/figure/section number), and a corrected sentence. Also list sentences
that understate a result the body proves. Answer in Chinese, quotes in English.
If you find nothing in a category, say so.
```

## 4. 主会话核实

- 子代理指出的每一个问题，都要回到正文核对：**确认**（修改）、**驳回**（写明理由），或**部分成立**。结果记录在 `blind/verification.md`。
- 子代理可能把正文里有的内容说成没有，也可能在数学上判断错误。Case B 的模拟审稿提出 3 项错误，主会话逐项复算后才确认。
- 揭开 A/B 对应关系，汇总：编辑子代理对新稿的一句话复述，是否与 spine 第 1 句一致；对原稿的复述又是怎样的。

## 5. 通过标准与迭代

- **通过**：编辑子代理对新稿的一句话复述与 spine 第 1 句在实质上一致，判定为送外审，或者拒稿理由不涉及表述；过冲审查没有经确认成立的问题。
- **不通过**：根据卡住的句子和确认成立的过冲问题修改一次，再用**新的**子代理重测，不能复用上一个，因为它已经看过答案。
- 第二次仍不通过：如实报告卡在哪里，并判断这是表述问题还是实质问题。如果拒稿理由是实质性的（新颖性不足、结果太弱、基线不公平），重写解决不了，要明确告诉用户。

## 6. 局限

模拟编辑是同一类模型扮演的，可能与真实编辑的偏好不一致。它的作用是检查"新意能不能被读出来"，不能预测录用结果。
