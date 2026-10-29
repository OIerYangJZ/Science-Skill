# Blind test: simulated editor and overclaim review

Both subagents must be **independent**: do not show them survey_report, polish_notes, the ledger, or the analysis in this conversation. Once a reviewing subagent has read the author's notes, its judgment is biased. In Case B, the reviewing subagent did not read the joint report, and the main session verified each point afterward.

Label every conclusion "inferred".

## 1. Prepare materials

Under `polish/<date>/blind/`, prepare:

- `A.txt`, `B.txt`: one for the original and one for the new draft, each containing title + abstract + introduction + Fig. 1 caption, either converted to plain text or kept as LaTeX. Decide at random which one is the new draft; record the mapping only in `blind/key.md`, never in the prompt.
- `criteria.txt`: verbatim excerpts of the journal's editorial standards from Pool C.
- The path to the full new draft for the overclaim review: body + appendices, with the abstract and introduction replaced by the new versions. If they have not been merged, give it the new abstract and introduction file together with the original body.

## 2. Editor test prompt

Use the Agent tool with subagent_type general-purpose. The prompt template is below; replace the content in angle brackets:

```
You are a handling editor at <journal>. You decide whether to send manuscripts
out for review. Editors at this journal apply these criteria (verbatim from the
journal's site):

<criteria.txt>

You have about five minutes per manuscript and read only what is below: title,
abstract, introduction, and the Fig. 1 caption. Two versions of the same
manuscript are in <path>/A.txt and <path>/B.txt. Read A first, write your
answers for A, then read B. Do not read any other file in the repository.

For each version, answer in <user's language> (quote English text verbatim
when you cite it):
1. State the main new result of this paper in one sentence. If you still cannot
   after reading, write "cannot tell" and indicate after which sentence you
   gave up looking.
2. Why it matters: what it changes, or whom it constrains.
3. What you consider the closest prior work, and how this paper improves on it.
   If the text does not name it, write "not named".
4. Send out for review or desk reject? Give 1–3 reasons, checked against the
   journal criteria above.
5. Which sentences you got stuck on (quote verbatim), and why.
6. Any sentences that made you feel the authors were being overly defensive or
   overclaiming (quote verbatim).

Then compare: which version lets an editor find the contribution faster, and
why? Which sentences in the better version would you still change?
Return everything as markdown.
```

## 3. Overclaim referee prompt

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
that understate a result the body proves. Answer in <user's language>, quotes
in English. If you find nothing in a category, say so.
```

## 4. Main-session verification

- Check every issue a subagent raises against the body: **confirmed** (revise), **rejected** (state the reason), or **partially valid**. Record the results in `blind/verification.md`.
- A subagent may claim that something present in the body is missing, or may misjudge the mathematics. In Case B, the mock review raised 3 errors, and the main session confirmed them only after recomputing each one.
- Reveal the A/B mapping and summarize: whether the editor subagent's one-sentence restatement of the new draft matches sentence 1 of the spine, and what its restatement of the original was.

## 5. Pass criteria and iteration

- **Pass**: the editor subagent's one-sentence restatement of the new draft substantively matches sentence 1 of the spine, and its verdict is to send out for review, or its rejection reasons do not concern presentation; the overclaim review has no confirmed issues.
- **Fail**: revise once based on the sentences it got stuck on and the confirmed overclaim issues, then retest with a **new** subagent. Do not reuse the previous one, because it has already seen the answer.
- Still failing on the second attempt: report honestly where it gets stuck, and judge whether this is a presentation problem or a substantive problem. If the rejection reasons are substantive (insufficient novelty, results too weak, unfair baseline), rewriting cannot fix them; tell the user so explicitly.

## 6. Limitations

The simulated editor is played by the same kind of model and may not match real editors' preferences. Its role is to check "whether the novelty can be read out"; it cannot predict acceptance.
