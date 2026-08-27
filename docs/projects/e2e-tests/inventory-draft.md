# Flow inventory — draft (bootstrap artifact)

**This file dies at ticket 08.** It exists to shard work across agents. Once the
suite generates `frontend/tests/FLOWS.md` from test titles, delete this.

Tiers: **A** = the merge gate, **B** = the 80% bar, **C** = beyond the bar.
Churn is files touched in `frontend/src2/<area>` over the 3 months to 2026-08-27.

---

## Query — churn 112 (highest)

| # | Flow | Tier |
|---|---|---|
| Q1 | A user picks a table as a query source and sees rows | A |
| Q2 | A user adds a filter and the row count falls | A |
| Q3 | A user adds a summarize and the grain changes | A |
| Q4 | A user joins a second table and sees its columns | A |
| Q5 | A user adds a mutate with an expression and sees the new column | A |
| Q6 | A user reorders operations and results follow | A |
| Q7 | A user removes an operation mid-pipeline | A |
| Q8 | A user renames and removes columns | B |
| Q9 | A user casts a column type | B |
| Q10 | A user sorts by a column | B |
| Q11 | A user sets a limit | B |
| Q12 | A user filters on a date with the relative date picker | B |
| Q13 | A user writes a native SQL query and runs it | B |
| Q14 | A user pivots wider | B |
| Q15 | A user unions two queries | B |
| Q16 | A user opens View SQL and sees compiled SQL | B |
| Q17 | A user adds a window operation | C |
| Q18 | A user applies conditional formatting | C |
| Q19 | A user writes a script query | C |
| Q20 | A user sets up a query alert | C |

## Charts — churn 76

| # | Flow | Tier |
|---|---|---|
| C1 | A user creates a Bar chart with one dimension and one measure | A |
| C2 | A user creates a Number chart and sees the value | A |
| C3 | A user creates a Table chart with rows, columns and values | A |
| C4 | A user creates a Donut chart | A |
| C5 | A user changes chart type and config survives where it can | A |
| C6 | A user sets a date dimension granularity to month | B |
| C7 | A user adds a split-by and sees series | B |
| C8 | A user adds a second measure | B |
| C9 | A user sorts a chart | B |
| C10 | A user filters a chart independent of its query | B |
| C11 | A user creates a Line chart | B |
| C12 | A user drills down from a chart into rows | B |
| C13 | A number card shows a comparison and a sparkline | B |
| C14 | A user creates Funnel, Bubble, Sankey, Map charts | C |
| C15 | A user shares a chart and opens the public link | C |

## Dashboard — churn 60

| # | Flow | Tier |
|---|---|---|
| D1 | A user creates a dashboard and adds a chart | A |
| D2 | A user adds a dashboard filter and linked charts refilter | A |
| D3 | A user moves and resizes a dashboard item | A |
| D4 | A dashboard loads with all charts rendered | A |
| D5 | A user adds a text block | B |
| D6 | A user removes a dashboard item | B |
| D7 | A user shares a dashboard and opens the public link | B |
| D8 | A dashboard filter with no linked chart warns | B |
| D9 | A user duplicates a dashboard item | C |

## Workbook — churn 83

| # | Flow | Tier |
|---|---|---|
| W1 | A user creates a workbook from the list | A |
| W2 | A user opens a workbook and switches query, chart, dashboard tabs | A |
| W3 | A user renames a workbook | A |
| W4 | A workbook saves and survives a reload | A |
| W5 | A user deletes a workbook | B |
| W6 | A user creates a folder and moves a workbook into it | B |
| W7 | A user shares a workbook with another user | B |
| W8 | A user opens a workbook template and it materializes | B |
| W9 | A user views workbook lineage | C |
| W10 | A user duplicates a query inside a workbook | C |

## Shared and guest views

| # | Flow | Tier |
|---|---|---|
| S1 | A logged-out visitor opens a shared dashboard link and sees charts | A |
| S2 | A logged-out visitor opens a shared chart link | B |
| S3 | A revoked public link stops working | B |

## Data source and data store — churn 12

| # | Flow | Tier |
|---|---|---|
| DS1 | A user browses a data source's table list and previews a table | A |
| DS2 | A user uploads a CSV and it becomes a queryable table | B |
| DS3 | A user connects a new database and the connection test reports | B |
| DS4 | A user imports a table into the Data Store | B |
| DS5 | A user removes a Data Store table | C |

## Permissions and teams

| # | Flow | Tier |
|---|---|---|
| P1 | A viewer sees only the workbooks granted to them | A |
| P2 | A viewer cannot edit a workbook they can read | A |
| P3 | An admin creates a team and grants a resource | B |
| P4 | A user without data source access cannot query it | B |

## Settings — churn 14

| # | Flow | Tier |
|---|---|---|
| ST1 | An admin changes a general setting and it persists | C |
| ST2 | An admin invites a user | C |
| ST3 | An admin changes Data Store settings | C |

---

## Counts

| Tier | Flows |
|---|---|
| A | 24 |
| B | 30 |
| C | 15 |
| **Total** | **69** |

A + B = 54 of 69 = **78%**. A + B + two C flows clears 80%.
