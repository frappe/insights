# Confirm the frappeverse build scripts match the database

Type: task
Status: open
Repo: insights

## Question

The six frappeverse boards are already preserved as build scripts in workshop commit `74f281b`, `efforts/frappeverse-insights-demo/build/`. Each script rebuilds its workbook from scratch on `demo.erpnext.localhost`:

| Workbook | Script |
|---|---|
| 47 Business Overview | `overview_board.py` |
| 49 Purchase & Payables | `purchase_board.py` |
| 54 Receivables | `receivables_board.py` |
| 55 Stock | `stock_board.py` |
| 56 HR | `hr_board.py` |
| 57 Selling | `sales_board.py` |

The written specs are in `assets/board-specs/`, and the conventions every board follows are in `build/BOARD-CONVENTIONS.md`.

Confirm that the scripts still describe what the database holds. All six workbooks were built on 2026-08-20. Only one set of edits came later: on 2026-09-02, Administrator modified four Selling number cards (Booked MTD, Booked Last Week, Win Rate, Average Order Value). Find out whether that was a hand edit or a migration patch rewriting chart config. Diff those four cards against `sales_board.py`, and check the other workbooks for drift the same way.

For each workbook that differs from its script, export `workbook.json` into `docs/projects/desk-dashboards/assets/<slug>/`. Record per workbook: whether it matches, what differs, and the path of any snapshot.

The scripts are fixed to the demo. Every window is anchored on 10 Aug 2026, and they read the demo dataset. They record what was reviewed, not what ships. Turning them into shipped content is ticket 06's work.
