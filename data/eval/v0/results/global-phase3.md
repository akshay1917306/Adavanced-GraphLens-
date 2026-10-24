# Global search against the baseline: dynamic selection (phase3)

Pairwise judge, order swapped; a criterion is won or lost only when both orders agree.
Win rate = (wins + half the ties) / questions. The interval is approximate.

| Criterion | Wins | Ties | Losses | Questions | Win rate | 95% interval |
|---|---|---|---|---|---|---|
| comprehensiveness | 20 | 0 | 0 | 20 | 100% | 84% to 100% |
| diversity | 20 | 0 | 0 | 20 | 100% | 84% to 100% |
| empowerment | 20 | 0 | 0 | 20 | 100% | 84% to 100% |
| directness | 1 | 16 | 3 | 20 | 45% | 26% to 66% |

Cost of this run: $0.0000. Questions judged: 20 of 20.

Judge and answerer are the same model family and the question set is small; read the interval, not only the rate.

## Per question

| Question | comprehensiveness | diversity | empowerment | directness |
|---|---|---|---|---|
| G01 | ours | ours | ours | tie |
| G02 | ours | ours | ours | tie |
| G03 | ours | ours | ours | tie |
| G04 | ours | ours | ours | tie |
| G05 | ours | ours | ours | tie |
| G06 | ours | ours | ours | tie |
| G07 | ours | ours | ours | tie |
| G08 | ours | ours | ours | tie |
| G09 | ours | ours | ours | tie |
| G10 | ours | ours | ours | tie |
| G11 | ours | ours | ours | baseline |
| G12 | ours | ours | ours | tie |
| G13 | ours | ours | ours | ours |
| G14 | ours | ours | ours | baseline |
| G15 | ours | ours | ours | tie |
| G16 | ours | ours | ours | tie |
| G17 | ours | ours | ours | baseline |
| G18 | ours | ours | ours | tie |
| G19 | ours | ours | ours | tie |
| G20 | ours | ours | ours | tie |

# Global search against the baseline: no selection, first 10 questions (phase3)

Pairwise judge, order swapped; a criterion is won or lost only when both orders agree.
Win rate = (wins + half the ties) / questions. The interval is approximate.

| Criterion | Wins | Ties | Losses | Questions | Win rate | 95% interval |
|---|---|---|---|---|---|---|
| comprehensiveness | 10 | 0 | 0 | 10 | 100% | 72% to 100% |
| diversity | 10 | 0 | 0 | 10 | 100% | 72% to 100% |
| empowerment | 10 | 0 | 0 | 10 | 100% | 72% to 100% |
| directness | 0 | 8 | 2 | 10 | 40% | 17% to 69% |

Cost of this run: $0.0000. Questions judged: 10 of 10.

## Per question

| Question | comprehensiveness | diversity | empowerment | directness |
|---|---|---|---|---|
| G01 | ours | ours | ours | tie |
| G02 | ours | ours | ours | tie |
| G03 | ours | ours | ours | tie |
| G04 | ours | ours | ours | baseline |
| G05 | ours | ours | ours | tie |
| G06 | ours | ours | ours | tie |
| G07 | ours | ours | ours | tie |
| G08 | ours | ours | ours | tie |
| G09 | ours | ours | ours | baseline |
| G10 | ours | ours | ours | tie |

## Spend

The figures above are for the last run (everything was cached, so it cost $0). The evaluation cost $0.2623 the first time and $0.0297 for a second run that redid five items after internet time-outs (three failed judge calls and two partial answers in the no-selection part). Total $0.2920.
