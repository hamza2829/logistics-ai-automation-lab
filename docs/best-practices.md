# Best practices for a logistics automation experiment

1. Define the boundary. Write down who starts the process, the step you want to change and who owns the final decision. Keep dispatch, driver scheduling and stock movements under staff control.
2. Establish a baseline. Record elapsed time, case volume, exceptions and rework. Define the clock and denominator. Compare by request type before drawing conclusions from the aggregate.
3. Prefer a narrow trial. Compare a deterministic baseline with the candidate on the same examples. Freeze the example set for measurement and use new examples for tuning.
4. Treat incoming text as untrusted. Use fictional or approved redacted data, validate fields, constrain outputs and keep integrations read-only during trials.
5. Inspect confident errors. Track exact accuracy, unflagged errors, false review flags and reviewer workload. A confidence value is useful only in relation to observed errors.
6. Give reviewers a way to reject a suggestion. Keep the original input and decision visible, and record who made the decision in any real deployment.
7. Define stop criteria before deployment. Agree on unacceptable mistakes, owners, rollback and a fallback path. Verify production access controls and retention separately.
