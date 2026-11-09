# Experiment log

All runs use synthetic inputs and a loopback-only environment.

| Experiment | Question | Method | Evidence and interpretation |
| --- | --- | --- | --- |
| E1. Process baseline | Where does the simulated flow wait and loop? | Generate requests from a fixed seed, then calculate elapsed time to the next step and count repeated visits per request. | The Actions artifact includes the report, dwell chart and directly follows graph. Bottlenecks reflect the simulator's configured distributions. |
| E2. Intake routing | Can the offline mock assign one of four categories or send a request to review? | Compare exact category labels across the full benchmark. Track all errors and unflagged errors separately. | The benchmark report lists the confusion matrix and every failure. Unfamiliar wording, mixed intents and incidental keywords are failure modes to inspect. |
| E3. Human decision | Does the workflow pause and resume when someone reviews a low-confidence request? | Use npx to import and publish the workflow, submit synthetic intake, and exercise approve and reject callbacks. | The committed run log records the actual statuses and outcomes. CI repeats the integration test on every run. The callback simulates a person in CI. |
| E4. Provider failure | Can triage still return a conservative result when the provider fails? | Inject a provider timeout, unavailability or an invalid response in pytest. | Fallback tests require the rules engine and a review flag. Rule-based confidence remains heuristic. |

The scorecard ranks hypotheses for a workshop. It does not supply measured business impact, a deployment decision or an expected labor saving.
