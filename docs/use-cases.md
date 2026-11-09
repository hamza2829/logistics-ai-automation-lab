# Logistics AI use case scorecard

Scores are workshop assumptions for a fictional service. A 1 is low and a 5 is high.
Rank by `2 × impact - effort - 2 × risk`. Break ties by lower risk, then lower effort, then case ID. A risk score of 4 or 5 triggers a hold for human assessment.

| Rank | Candidate | Service area | Impact | Effort | Risk | Score | Decision |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | Classify incoming service requests | Shared intake | 5 | 1 | 2 | 5 | Candidate for experiment |
| 2 | Identify missing booking details | Driver bookings | 4 | 2 | 1 | 4 | Candidate for experiment |
| 3 | Draft a shift handover summary | Dispatch | 3 | 2 | 1 | 2 | Candidate for experiment |
| 4 | Summarize warehouse order exceptions | Warehouse orders | 4 | 3 | 2 | 1 | Candidate for experiment |
| 5 | Draft parcel status replies | Mail and parcel | 4 | 2 | 3 | 0 | Candidate for experiment |
| 6 | Summarize alternatives for a route change | Dispatch | 5 | 5 | 4 | -3 | Hold for assessment |
| 7 | Suggest eligible driver slots | Driver bookings | 5 | 4 | 5 | -4 | Hold for assessment |

## Classify incoming service requests

- Hypothesis: A suggested route could reduce first-pass sorting work for the service desk.
- Measure: Exact category accuracy, unflagged errors, and review workload.
- Boundary: Confirm ambiguous requests with a human before assigning them.

## Identify missing booking details

- Hypothesis: Highlighting missing fields could reduce requests returned for clarification.
- Measure: Missing-field recall and unnecessary clarification requests.
- Boundary: A clerk confirms the checklist and contacts the requester.

## Draft a shift handover summary

- Hypothesis: Drafting a summary could reduce repeated reading at shift change.
- Measure: Omitted exceptions and time to review the draft.
- Boundary: Use only the supplied event records and require human sign-off.

## Summarize warehouse order exceptions

- Hypothesis: A grouped explanation could help reviewers identify recurring order returns.
- Measure: Missed exception causes and time to inspect a batch.
- Boundary: Keep order data read-only and preserve source IDs.

## Draft parcel status replies

- Hypothesis: A draft grounded in recorded events could reduce reply preparation time.
- Measure: Unsupported statements, correct status references, and review time.
- Boundary: The clerk verifies the source event and sends the reply.

## Summarize alternatives for a route change

- Hypothesis: A comparison of proposed routes could help a dispatcher respond to a disruption.
- Measure: Missed constraints, suggested travel differences, and dispatcher overrides.
- Boundary: A dispatcher approves all route decisions and safety constraints.

## Suggest eligible driver slots

- Hypothesis: Candidate slots could reduce repetitive lookup for planners.
- Measure: Invalid suggestions and time to confirm eligibility.
- Boundary: Enforce scheduling constraints separately and keep booking with a dispatcher.
