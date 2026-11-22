# Financial algorithm test results

Date: 2026-11-22. These are the tests that were executed. They are not a
production load test and they are not a claim that the engine detects crime.

## Commands

Backend, from `backend/`:

- `python -m ruff check src tests` — passed
- `python -m mypy src` — passed, 41 source files
- `python -m pytest -q` — **61 passed**, 1 Starlette deprecation warning about `httpx`

Frontend, from `frontend/`:

- `eslint src` — passed
- `tsc --noEmit` and `vite build` — passed
- `vitest run` — 2 passed

The 3,000-row chain test asserts completion in under 2 seconds and exactly 3
published flows. The measured time was not recorded beyond that bound.

## Labelled comparisons

Ground truth is `analysis_ground_truth()` and the rows in the unit tests. It
was written from the scenario tables, not from detector output. Precision and
recall below are for those labelled sets only. They are not a population rate.

| Labelled set | Expected | Result | Precision | Recall |
| --- | --- | --- | --- | --- |
| Horizon 3 chain hops | V→I1, I1→I2, I2→I3 | Those three flows, amounts `100000.0000` | 1 | 1 |
| Horizon 3 residual | I3 `outside_horizon`, B absent | Matched | — | — |
| Horizon 4 | B is the last destination | Matched, no residual | 1 on that hop set | 1 |
| Unrelated `100000` pair in the same case | Not on the seeded path | Absent | true negative | — |
| Fan-in, 3 verified sources, minimum 3 | `FAN_IN` on `****0030`, support credits | Fired | 1 | 1 |
| Fan-in minimum 4, same rows | No `FAN_IN` | None | true negative | — |
| Two sources plus a narration credit | No `FAN_IN` | None | true negative | — |
| Fan-out, 4 destinations | `FAN_OUT` | Fired | 1 | 1 |
| Pass-through at ratio `0.85` on `40000/60000` | Does not fire | Did not fire | true negative | — |
| Pass-through at ratio `0.50`, dwell 48 hours, clocks about 30 hours apart | Fires, dwell sentence present | Fired | 1 on that account | 1 |
| Date-only pass-through | Fires without a dwell claim | Limitation says dwell was not applied | — | — |
| Outflow 48 hours after inflow, dwell 24 | Does not fire | Did not fire | true negative | — |
| Return A→B→A | Walk stops, no `CYCLE` code | `returned_to_earlier_account` | — | — |

Repeated FIFO and indicator calls on the same rows returned the same
`output_hash`. A second API trace inserted a new run id and still three flows,
not six.

## Other checks

- Same-day null times spend the lower line number first.
- A same-reference reversal nets. A different reference does not.
- A `100` debit against a `40` attributed lot emits `40.0000` only.
- `0.1000` and `0.2000` stay exact after a `0.3000` seed.
- A cash exit has a null destination.
- An injected extra outflow fails conservation and the API stores zero
  `trace_flows`.
- An auditor assigned to the case receives 403 on `POST` trace and 200 on
  `GET`. An unassigned investigator receives 404. An assigned analyst can run
  a trace. `max_layer` 6 is 422.
- Activity keeps `10.1000` INR and `10.2000` USD apart. The INR average of
  `10.1000` and `0.3000` is `5.2000`.

## Not measured

No database `EXPLAIN`, no multi-user load, no memory profile, and no case at
the 10,000-row cap. The 2-second bound is a regression check on one chain.
