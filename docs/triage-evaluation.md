# Synthetic triage benchmark

The deterministic mock was evaluated offline. Exact category matches count as correct. Cases sent to review still count in the denominator.

- Accuracy: **59/80 (73.75%)**.
- Flagged for review: 28/80.
- Incorrect categories without a review flag: 8.

## Confusion matrix

| Expected / predicted | mail_parcel | dispatch | driver_booking | warehouse_order | other |
| --- | ---: | ---: | ---: | ---: | ---: |
| mail_parcel | 13 | 1 | 0 | 0 | 2 |
| dispatch | 0 | 13 | 0 | 1 | 2 |
| driver_booking | 0 | 3 | 11 | 0 | 2 |
| warehouse_order | 1 | 2 | 0 | 11 | 2 |
| other | 2 | 1 | 1 | 1 | 11 |

## Every incorrect category

| Request | Expected | Predicted | Score | Review | Synthetic request text |
| --- | --- | --- | ---: | --- | --- |
| SYN-T002 | warehouse_order | dispatch | 0.66 | yes | Maple site: Update the warehouse order after the dispatch load plan changes. |
| SYN-T005 | driver_booking | other | 0.20 | yes | Birch site: Allocate a licensed colleague to cover the next run. |
| SYN-T013 | other | dispatch | 0.86 | no | Cedar site: The annual dispatch team survey link is broken. |
| SYN-T019 | other | warehouse_order | 0.86 | no | Alder site: A warehouse order appears in the slide deck, but I only need spelling checked. |
| SYN-T020 | warehouse_order | other | 0.20 | yes | Birch site: Move six cartons from the upper rack to the lower staging area. |
| SYN-T024 | driver_booking | dispatch | 0.48 | yes | Cedar site: The load plan is confirmed, but check driver availability. |
| SYN-T025 | driver_booking | dispatch | 0.86 | no | Alder site: The route sheet is ready; we need a person who can drive the van. |
| SYN-T036 | other | driver_booking | 0.86 | no | Birch site: The driver booking icon on the intranet is blurry. |
| SYN-T037 | warehouse_order | other | 0.20 | yes | Cedar site: The inventory rack needs four more boxes before the next shift. |
| SYN-T040 | driver_booking | dispatch | 0.48 | yes | Birch site: Change the driver booking for the outbound route. |
| SYN-T043 | driver_booking | other | 0.20 | yes | Birch site: Is anyone available to take the wheel on the late shift? |
| SYN-T044 | dispatch | other | 0.20 | yes | Alder site: Change the order in which the vans visit our sites. |
| SYN-T048 | other | mail_parcel | 0.86 | no | Cedar site: I want to change the email footer used by the mailroom. |
| SYN-T049 | dispatch | warehouse_order | 0.86 | no | Maple site: The warehouse order is already staged; decide which van will collect it. |
| SYN-T053 | warehouse_order | dispatch | 0.48 | yes | Alder site: The outbound route uses the same slot; update the bin location first. |
| SYN-T055 | mail_parcel | other | 0.20 | yes | Cedar site: Where should we drop stamped letters for the afternoon collection? |
| SYN-T056 | mail_parcel | dispatch | 0.86 | no | Alder site: The route sheet is printed, but the actual request is to find a missing envelope. |
| SYN-T067 | other | mail_parcel | 0.48 | yes | Cedar site: Someone left a parcel and a route sheet in the meeting room. |
| SYN-T072 | warehouse_order | mail_parcel | 0.86 | no | Maple site: A parcel label was attached, but the request is to move stock between racks. |
| SYN-T074 | mail_parcel | other | 0.20 | yes | Birch site: A padded packet for the training office is missing from reception. |
| SYN-T076 | dispatch | other | 0.20 | yes | Cedar site: Which van should take the returns to the consolidation point? |

Scores are heuristic. Template coverage and failure frequencies are properties of this synthetic benchmark.
