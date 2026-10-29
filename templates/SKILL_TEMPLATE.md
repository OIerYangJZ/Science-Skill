---
name: <kebab-case-name>
description: <One or two sentences on what it does, when to use it, and when not to use it. The model relies on this text to decide whether to invoke the skill automatically, so state the trigger situations clearly.>
argument-hint: "[argument description]"
---

# <name>: <one-sentence goal>

## The problem this skill addresses

<Which item of FAILURE_MODES.md it corresponds to; state the symptoms and one piece of observed evidence.>

## Hard rules

1. Do not overwrite the user's originals; write outputs to `<artifact-dir>/<YYYY-MM-DD>/`.
2. <Specific requirements for putting evidence before conclusions>
3. Label every simulated judgment "inferred".
4. Talk to the user in their language; papers and code keep their original language.

## Workflow

### Phase 0: Intake
<What needs to be determined; what can be inferred and what must be asked of the user>

### Phase 1 … N
<For each step: inputs, actions, output files, acceptance criteria>

### Independent verification
<Verify with a subagent or a script; the main session checks the subagent's conclusions>

## Final report
<Key points for the user, in the user's language: conclusions, file paths, items that need confirmation, parts that could not be done>
