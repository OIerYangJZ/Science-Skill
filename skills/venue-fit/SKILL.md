---
name: venue-fit
description: Decide where to submit a manuscript using verified facts instead of impressions. Builds a candidate list from where similar work is actually published, profiles each venue (type, publisher, open-access status, listed fees, output), collects every decision-relevant fact from the venue's official pages with URL, date checked and a verbatim snippet (scope, editorial criteria, article types and limits, review model, fees and waivers, preprint, AI and data policies, concurrent-submission and transfer rules, deadlines, anonymity, archival status), assesses fit against the manuscript and the author's constraints, and proposes a primary venue, fallbacks and compatible low-cost parallel options with a deadline calendar. Any discipline, journals and conferences. Use when choosing or changing the target venue, after a rejection, or before committing to a deadline. Not for preparing the submission package itself or for polishing the text (paper-polish).
argument-hint: "[manuscript] [candidate venues, optional] [--budget <APC limit>] [--deadline <date>]"
---

# venue-fit: choose a venue from verified facts

## The problem this skill addresses

Venue decisions are often made from memory and impressions, and AI assistants are confident about venue facts that change every year (item 8 of `FAILURE_MODES.md`). In the observed case, a venue survey corrected several assumptions only after reading the official pages:
- a venue assumed to be a conference was a journal;
- a major conference had introduced new rules for the year: non-anonymous submission, public posting of all submissions, a mandatory author video, and a disclosure statement for substantial LLM use;
- a talk submission was not automatically considered for the poster track, which had its own submission and deadline;
- the same publisher's site listed two different fees for one journal;
- after an editorial rejection, a resubmission to the same journal had to be "substantially new"; within one publisher family, a transfer could keep the original received date;
- when a manuscript was retargeted, its cover letter still argued fit for the previous journal.

The same result can also be judged "standard" by one community and "new" by another, so the novelty verdict and the venue choice depend on each other.

## Hard rules

1. **Facts come from official sources, with URL and date.** Scope, criteria, fees, deadlines and policies are taken from the venue's own pages, or the publisher's or the conference's call for papers. Record the URL, the date checked, and a short verbatim snippet. Bibliographic databases (OpenAlex) and memory are pointers for screening only.
   - Example: OpenAlex lists a start year decades before one journal was founded.
   - When a page cannot be fetched, use search-result snippets marked "snippet, confirm on site", or ask the user to open the page.
2. **Unknown stays unknown.** Never fill a fee, deadline or policy by inference. A fact sheet with "unknown" rows is better than a wrong one.
3. **The decision is the user's.** Present options with reasons; label inferences (for example, desk-reject risk) as inferred.
4. **No submission actions.** Do not register accounts, submit, pay, or contact editors.
5. Talk to the user and write reports in the user's language.

## Phase 0: Intake

- **The manuscript.** Genre (theory, method, experimental, clinical, computational, review), length, figures, and whether a preprint is already public.
- **Constraints.**
  - fee budget and possible waivers;
  - funder or institutional open-access mandates;
  - deadlines;
  - journal versus conference expectations in the field and for the author's career stage;
  - anonymity needs;
  - co-author preferences.
- **History.** Previous submissions of this work, decisions and stated reasons, and the rules on resubmission and transfer.
- **Novelty verdict.** If `novelty-audit` has been run, which communities would see the result as new and which as standard.
- **Candidate venues** the user already has in mind.

## Phase 1: Long list (where similar work is published)

```
V="python3 -I <skill-dir>/scripts/venue_fit.py"
$V neighbors --query '"<key phrase>" AND "<key phrase>"' --from 2021 --types journal,conference
$V neighbors --seed <DOI of the nearest prior work> <DOI ...> --from 2019
```

`neighbors` aggregates the venues of related works (matching the query, and citing or cited by the seed papers). It reports counts, median citations and example titles. Full-text matching is noisy: use precise phrases and seed papers, and ignore venues that are clearly off-field.

Add:
- the user's candidates;
- the field's main conferences or journals;
- venues suggested by the novelty verdict (a community that sees the work as new);
- low-cost parallel options: posters, workshops without proceedings, talks.

Aim for 8–15 candidates.

## Phase 2: Screening profiles

```
$V profile "<venue name or ISSN>" ...
```

Screen by type, scope, size, open-access model and listed fees. These values come from OpenAlex and are used only to shortlist 3–6 venues. Exact names or ISSNs avoid ambiguous matches; the script warns when it had to guess.

## Phase 3: Official fact sheets (shortlist)

```
$V factsheet "<venue>" "<venue>" --out venue/<date>/factsheets.md
```

For every shortlisted venue, fill each row of the template from official pages:
- scope (verbatim);
- editorial criteria (verbatim);
- article types and limits;
- abstract format;
- review model;
- fees and waivers;
- open-access license;
- preprint policy;
- AI/LLM policy;
- data and code policy;
- required reporting guidelines;
- concurrent submission, resubmission and transfer rules;
- deadlines with time zone;
- anonymity and public posting;
- archival status;
- time to decision, if published;
- template and submission system.

Each row has a value, a URL, a date checked and a snippet. Note conflicting statements on the same site (for example, two fee figures) instead of choosing one silently.

## Phase 4: Fit assessment

For each shortlisted venue, write short reasoned ratings (good / possible / poor, with the reason), not an opaque score:

| Dimension | Question | Evidence |
|---|---|---|
| Scope | Has the venue published comparable work recently? | Phase 1 counts and named examples |
| Bar | Does the contribution meet the venue's stated criteria? Would its community see the result as new? | Criteria snippet; novelty verdict |
| Format | Do length and type limits fit? What is the reformatting cost? | Limits versus manuscript |
| Audience | Will the people who should read or cite this work read this venue? | Neighbor venues of key citing works |
| Cost | Do fees fit the budget? Are waivers or memberships available? | Fees row |
| Timeline | Do deadlines and decision times fit the author's constraints? | Deadline rows |
| Policy compatibility | Preprint already posted; anonymity; AI disclosure; data and code requirements | Policy rows |
| History | Rules after a previous rejection; transfer options | History, policy rows |
| Risk | Plausible desk-reject reasons (inferred) | Criteria versus the manuscript's weak points |

## Phase 5: Recommendation and plan

Write `venue/<date>/plan.md` in the user's language:
1. **Primary venue**, with the deciding reasons and the main risk.
2. **Fallbacks** in order, including transfer paths that keep the review history where they exist.
3. **Compatible parallel options** (posters, non-archival workshops, talks), each checked against the concurrent-submission and archival rules of the primary venue.
4. **Calendar.** Every deadline with date, time zone (e.g. AoE) and what is due. On request, write an `.ics` file.
5. **Actions before submitting:**
   - reformat to the template and limits;
   - write a cover letter for this venue (not the previous one);
   - complete required statements (AI use, data availability, reporting checklist);
   - check that the preprint policy fits.

   Hand off to the relevant skills (`paper-polish`, `number-audit`, `cite-verify`).
6. **Unknowns** that still need confirmation, with whom to ask (editorial office, program chairs).

## Final report to the user (concise, in the user's language)

- The recommended primary venue and fallbacks, one line each with the deciding reason.
- The nearest deadlines.
- Facts that could not be confirmed.
- The paths of the fact sheets and the plan.
