# Pre-registered outcome narratives

**Written 1 October 2026.** The forecast archive was fetched this morning and
verified structurally — 4,404,312 rows across 68 chunks, row counts matching
times by fields exactly, every model reaching 2026-09-30T23:00. Nothing in it
has been joined to a reference, scored, or inspected beyond the structural
check. No metric has been computed.

No observational reference has been fetched for scoring; only catalogue
metadata has been read.

**Why this exists.** Once numbers exist, any interpretation written for them
can be reverse-engineered from them. "The model is skilful where it matters"
is easy to write after seeing where it is skilful. Fixing the interpretations
first means the numbers select an outcome rather than the outcome selecting
its justification.

**Fixed here:** the shape of each conclusion and what follows from it.
**Not fixed here:** the numeric thresholds X, Y and Z, which live in
`protocol/gate_thresholds.json`, set before results are read and committed
separately so the decision rule and the decision cannot be confused.

---

## The unit of judgement

Not "the forecast". A single verdict would hide the thing Roger needs,
because temperature at lead 1 and rainfall at lead 7 are different products
with different prospects.

Every judgement is made per **(variable, lead day)** cell, and only then
rolled up.

Each cell reports:

- **skill against its named baseline**, not absolute error. A model with
  1.5 degC mean absolute error is useless if persistence achieves 1.2 degC.
  Absolute error is reported too, because operators think in it, but it
  decides nothing.
- **forecast coverage** and **reference coverage**, separately.
- **n**, the count of scored pairs, and the count dropped.
- **monthly reference coverage**, travelling with every pooled figure.

## The baselines

| variable | baseline | source |
|---|---|---|
| temperature | climatology and persistence | protocol section 7 |
| shortwave / DNI | smart persistence on the clear-sky index | A3.4, clear-sky model per A5.3 |
| precipitation | base rate at each threshold | A3.5, A5.6 |
| cloud cover | relative ranking only, no absolute skill claim | A5.11 |

---

## Outcome A — sufficient

**Condition.** Skill against the named baseline exceeds threshold X, with
coverage at or above the bar set in A5.1.

**What it means.** For that variable at that lead, a forward forecast exists
for Barbados that beats the naive alternative by a margin worth the
dependency. Roger's question — is there something real to build on — is
answered yes for that cell.

**Recommendation.** The variable is admitted at that lead as an input to the
load forecasting model. The source, the model identifier and the measured
skill are recorded so the load model's own error can later be attributed.

**What Outcome A does not establish.** That the load forecast will improve.
This assessment measures weather forecast skill. Whether that translates into
load forecast accuracy depends on how strongly load responds to the variable
at this scale, which is a separate measurement on BL&P's own load data and is
not attempted here. Outcome A says weather is not the limiting factor. It does
not say the model will work.

---

## Outcome B — conditional

**Condition.** Skill lies between thresholds Y and X, or exceeds X while a
stated limitation applies — thin reference coverage, a reference with known
bias, a lead where the archive is short.

**What it means.** There is real signal and it is not clean. The forecast
beats the baseline by a margin where operational value depends on how the
output is used and how much error the downstream process tolerates.

**Recommendation.** Admitted at that lead **with its limitation stated in the
same sentence as its admission**, never in a footnote. Where the limitation is
a short archive or a biased reference, the specific additional measurement
that would resolve it is named, with what it would cost.

**What Outcome B does not establish.** Which way the decision should go. B
hands a judgement to BL&P rather than making it. The assessment's job in B is
to state the margin, the limitation and the cost of resolving it precisely
enough that the judgement can be made on evidence.

---

## Outcome C — insufficient

**Condition.** Skill falls below threshold Z, or coverage falls below the A5.1
bar and cannot be repaired within the frozen window.

**What it means.** The available forecast does not beat the named baseline
by the pre-specified margin required for this assessment.

**Recommendation.** Excluded at that lead. If the failure is specific to lead
time, the shorter leads that passed are stated explicitly, so a seven-day
failure is not read as a one-day failure.

**What Outcome C does not establish.** That load forecasting for Barbados is
infeasible. It establishes that a particular input, from the sources assessed,
at that lead, is not usable. Other sources exist that this assessment did not
cover — a licensed ECMWF feed, a regional model run locally, an on-island
network feeding statistical downscaling. C is a result about what was
measured, and the honest version of C names what was not.


---

## Rolling cells up

The overall recommendation is not a vote. It is a matrix of cells with their
outcomes, followed by:

1. **The shortest lead at which every required variable reaches A or B.** The
   operational answer to "how far ahead can this work".
2. **The binding variable** — the one that fails first as lead extends. Named
   explicitly, because it is where any future investment should go.
3. **Whether Roger's stated operational horizon falls inside that range.** If
   the protocol needs a Tuesday 23:00 cutoff for the week ahead and the
   forecast is usable to lead 3, that is the finding, however good lead 3 is.

A single overall A, B or C is written only if every cell agrees, which is
unlikely and will not be manufactured.

---

## What none of the three outcomes establish

Recorded here so it cannot quietly be dropped later.

- **Translation to load error.** Stated under Outcome A; it applies to all
  three. This assessment measures weather forecast skill, not load forecast
  improvement.
- **Spatial generalisation.** Every measurement is at a single point,
  13.07333 N, 59.5 W, against a single observational reference. Skill there is
  not skill across the island, and nothing here tests the difference.
- **Temporal generalisation.** The verification window spans roughly two and a
  half years. It does not establish performance in an anomalous year, and a
  hurricane season or ENSO swing outside that range is untested.
- **Operational availability.** Whether an archived forecast existed is a
  different question from whether it had arrived in time to be used. The
  latency collector measures that and it is reported separately, never folded
  into skill.
- **Seasonal balance.** Where reference coverage varies by month, a pooled
  score is weighted towards the months the reference exists. Monthly coverage
  travels with every pooled figure for this reason. No rule suppresses a
  pooled figure on the basis of imbalance; the imbalance is reported and the
  reader judges it.
- **Deployment licensing.** Open-Meteo's data licence is CC BY 4.0 and permits
  commercial use with attribution; the free API tier's terms separately
  restrict access to non-commercial use under 10,000 calls a day. The BCO
  licence rests on written confirmation from MPI-M, version unspecified, with
  nothing stated on the portal. None of this is a skill finding.

---

## Sign-off

| item | signed | date |
|---|---|---|
| Outcome A condition and consequences | | |
| Outcome B condition and consequences | | |
| Outcome C condition and consequences | | |
| Roll-up rule | | |
| The six non-establishments | | |

Thresholds X, Y and Z are in `protocol/gate_thresholds.json`, committed
separately and before any result is read.
