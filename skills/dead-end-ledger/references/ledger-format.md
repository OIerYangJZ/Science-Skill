# 账本格式、笔记状态声明与汇报措辞

## 1. 账本结构（`ledger.py init` 生成）

```markdown
# Research ledger: <goal>

**Status (YYYY-MM-DD): <一句话，精确：确立了什么，没确立什么>.**

Goal: <精确的目标陈述>
Current best: <结果>（<状态>，<证据>）

## 1. Results
| ID | Result (exact statement or pointer) | Status | Evidence | Reviewed / verified (by, date) |

## 2. Data and numerical evidence
| ID | Test / experiment / analysis | Range or sample covered | Result | Evidence |

## 3. Open targets (ranked)
| ID | Target statement | Would give | Why hard / barrier |

## 4. Routes tried
| ID | Date | Route (one line) | Outcome | Stops at (barrier or step) | Evidence | Reopen only if |

## 5. Barriers
| Barrier | What it says | Routes that hit it |

## 6. Log
- YYYY-MM-DD: ...
```

**从 HANDOFF 式交接文档迁移：**

- "已证结果"表：按复核情况拆成 VERIFIED 和 UNVERIFIED（脚本也接受 PROVED-REVIEWED / PROVED-UNREVIEWED 的写法）。标注为 "sketch only, not written up" 的条目，应标 PRELIMINARY 或 UNVERIFIED，不能标 VERIFIED。
- "已试路线及止于何处"表：补上 Outcome 列（多为 FAILED）和 Reopen only if 列。例如某条路线止于一个已知的经典估计，Reopen only if 就写"出现比该估计更好的界"。
- 散落在各份笔记里的障碍，汇总进 Barriers 表，并写明每个障碍挡住了哪些路线。

**其他领域的路线表示意：**

| ID | Date | Route | Outcome | Stops at | Evidence | Reopen only if |
|---|---|---|---|---|---|---|
| X4 | 2026-03-02 | Pd 催化偶联，换配体 L1–L6 | FAILED | 底物在 60 °C 以上分解，产率均 < 15% | `notebook/2026-03-02.md` | 找到低温下有活性的催化体系 |
| X7 | 2026-05-10 | 在模型中加入对比学习损失 | NEGATIVE | 5 个种子的均值 +0.2 ± 0.6，在噪声范围内 | `runs/x7/summary.csv` | 换用更大的数据集，或者修改损失温度的搜索范围 |
| X9 | 2026-06-01 | 按地区分层分析政策效应 | PARTIAL | 只有一个地区显著，且为事后分析 | `analysis/x9.R` | 有新的数据可以预注册检验 |

## 2. 笔记开头的状态声明

```markdown
# <题目>

Date: YYYY-MM-DD. Continuation of <ledger ID / 上一份笔记>.

## Status

**<目标陈述> has not been proved. <不主张的内容，例如 No unconditional bound beyond b is claimed.>**

The results established in this note are:
- <结果 1>（PROVED-UNREVIEWED / CONDITIONAL(H) / HEURISTIC）
- …
What failed: <路线> stops at <步骤或障碍>.
```

## 3. 汇报措辞对照

| 不要说 | 除非 | 应该说 |
|---|---|---|
| "解决了 / proved / 做成了"（对目标） | 账本中目标对应的结果是 VERIFIED | "目标尚未达到；目前确立的最强结果是 X（已复核）" |
| "基本证明了"、"只差一小步" | 永远不说 | "证明在第 k 步缺少 Y；Y 是一个独立的未解决命题（相当于 Z）" |
| "数值证实了 X" | — | "在 k ≤ 16 范围内的数值与 X 一致；这不构成证明，也不覆盖 L≈30–80 的关键区间" |
| "应该很容易补完" | 已经写出并核对过 | "剩下的步骤是 Y；我还没有写出它" |
| "新思路有望突破" | — | "这条思路与已失败的路线 X3 的区别是 …；它能否越过 <障碍>，取决于 …" |
| "实验成功了" | 已经重复 | "单次实验得到 …（n = …）；尚未重复" |
| "方法有效 / 显著提升" | 多种子，并且在未调参的数据上 | "在 5 个种子上平均 +1.8（s.d. 0.4），验证集已用于调参，测试集结果待报告" |
| "趋势显著"、"接近显著" | 永远不说 | "差异为 …（95% CI …），未达到预设的显著性水平" |
| "数据支持我们的假设" | 预先设定的检验 | "预先设定的主要分析 …；另有探索性分析显示 …（未经确认）" |
| "取得重大进展" | — | 具体说：从 a 提高到 b（状态），或者排除了 n 条路线（列出） |

## 4. 复核子代理提示词

### 4a 证明复核

```
You are checking a proof, not improving it. Read only <proof file / sections>
and the definitions it cites (<files>). Do not read the author's notes, the
ledger or earlier reviews.

Go step by step. For each step: is it correct as written, correct with a fixable
gap (state the fix), or wrong (give a counterexample or the failing estimate)?
Check every constant and exponent that the conclusion depends on; recompute
numerics where possible and record the commands.

End with: VALID / VALID WITH FIXES (list) / INVALID (first fatal step), and
what you did not check. Answer in Chinese; mathematics in LaTeX.
```

### 4b 实验或计算结果复核（他人重跑）

```
You are re-checking a result, not improving it. Use only <raw data / code /
protocol paths> in a fresh copy (<work dir>). Do not read the author's notes
or the ledger.

Re-run the analysis or computation from the raw inputs. Record the exact
commands, versions, seeds and sample sizes. Compare every reported number
with your re-run at its displayed precision. Check that the evaluation data
were not used for tuning, that exclusions follow the stated rule, and that
the statistical test matches the design.

End with: REPRODUCED / REPRODUCED WITH DIFFERENCES (list) / NOT REPRODUCED
(first point of divergence), and what you could not check. Answer in Chinese.
```

