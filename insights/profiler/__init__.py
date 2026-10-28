# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Find out why dashboards load the data store until the host runs out of CPU.

Four instruments, because no one of them sees everything:

- `recorder` is passive. While it is switched on it writes a start and an end
  for every Insights request, every query, every warehouse open and every
  Insights background job. A failed query, a worker killed mid-query and a
  read refused by an import's write lock leave nothing anywhere else.
- `job` is active. In a background worker, where no request timeout cuts it
  short, it builds a dashboard's statements the way a reader's load builds
  them, profiles each inside DuckDB, runs the settings and concurrency
  experiments, replays the load as the browser sends it, and snapshots the
  processes, the host and the warehouse.
- `replay` runs on an operator's machine. It loads a dashboard over HTTP, as N
  readers would, so gunicorn, the limiter and nginx are part of what is measured.
- `report` reads the recorder's events back: what ran, what failed and why,
  what overlapped what, minute by minute.

`insights.api.profiler` exposes all of it to an Insights Admin, so nothing here
needs a shell on the host.
"""
