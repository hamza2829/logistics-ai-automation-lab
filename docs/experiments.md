# Experiment log

All runs use synthetic inputs and a loopback-only environment.

| Experiment | Question | Method | Evidence and interpretation |
| --- | --- | --- | --- |
| E1. Process baseline | Where does the simulated flow wait and loop? | Generate requests from a fixed seed, then calculate elapsed time to the next step and count repeated visits per request. | The run observed 3,000 completed requests and 427 with rework. The queue had the longest p90 dwell. See the [process report](process-report.md). |
| E2. Intake routing | Can the offline mock assign one of four categories or send a request to review? | Compare exact category labels across the full benchmark. Track all errors and unflagged errors separately. | The mock matched 59/80 categories. 8 incorrect predictions escaped review. The [benchmark report](triage-evaluation.md) lists every miss. |
| E3. Human decision | Does the workflow pause and resume when someone reviews a low-confidence request? | Use npx to import and publish the workflow, submit synthetic intake, and exercise approve and reject callbacks. | The [committed run log](n8n-run.log) records HTTP 422 for invalid intake, 202 for pending review, and 200 for both callbacks. [Source Actions run](https://github.com/hamza2829/logistics-ai-automation-lab/actions/runs/42688510338). CI repeats the integration test on every run. The callback simulates a person in CI. |
| E4. Provider failure | Can triage still return a conservative result when the provider fails? | Inject a provider timeout, unavailability or an invalid response in pytest. | Fallback tests require the rules engine and a review flag. Rule-based confidence remains heuristic. |

The scorecard ranks hypotheses for a workshop. It does not supply measured business impact, a deployment decision or an expected labor saving.
