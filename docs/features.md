# Features

One row per thing a user can do or rely on. Slugs are `<area>.<feature>` in the words of `CONTEXT.md`. The tests that pin each row are listed in `docs/coverage.md`, generated from the `@feature` directives on the tests.

## query

| Slug | Feature |
|---|---|
| query.source-table | A user picks a table as a query's source and sees its rows. |
| query.source-query | A user picks another query in the workbook as a source. |
| query.source-cycle-refused | Two queries cannot source each other. |
| query.interface-picker | A new query opens as a builder, a SQL editor or a script editor. |
| query.execute | A user runs the query and the result pane shows rows and columns. |
| query.row-count | The result pane states the total row count, and a reader's filter retires it. |
| query.select-columns | A user chooses which columns the result keeps. |
| query.select-columns-order | A user reorders the chosen columns by dragging. |
| query.remove-column | A user removes a column from the result. |
| query.rename-column | A user renames a column. |
| query.cast-column | A user changes a column's data type. |
| query.filter | A user adds a filter and the row count falls. |
| query.filter-and-or | A user joins filter rows with And or Or. |
| query.filter-operators-by-type | The operators offered depend on the column's type: text, number or date. |
| query.filter-number-range | A number filter offers presets cut from the column's own smallest and largest values, and a between range. |
| query.filter-values | A text filter offers the column's distinct values to pick from. |
| query.filter-relative-date | A user filters on a date with the relative date picker: last, current or next N days, weeks, months, quarters, years or fiscal years. |
| query.filter-relative-date-include-current | A relative date span can take in the current period. |
| query.filter-relative-date-shift | A relative span can be measured from a shifted anchor rather than today. |
| query.filter-is-set | A user filters rows to those with or without a value. |
| query.filter-expression | A user converts a filter row into a free-form expression. |
| query.filter-row-duplicate | A user duplicates or removes one filter row. |
| query.filter-from-column-header | A user builds a quick filter from a result column's header menu. |
| query.join | A user joins a second table and sees its columns. |
| query.join-type | A user picks an inner, left, right or full join. |
| query.join-columns-to-add | A user picks which columns of the joined table the result takes. |
| query.join-expression | A user writes a free-form join condition instead of matching two columns. |
| query.union | A user appends the rows of another table or query. |
| query.union-distinct | A user drops duplicate rows after appending. |
| query.mutate | A user adds a calculated column from an expression and sees it in the result. |
| query.mutate-inline | A user adds a calculated column from the empty column at the end of the grid. |
| query.expression-validation | An expression with a syntax error or an unknown column is refused with a message that names the problem. |
| query.expression-cannot-run-code | An expression is checked without being executed and cannot escape into arbitrary code. |
| query.expression-cannot-reach-files | An expression cannot read or write files or open connections. |
| query.expression-json | An expression reads a key out of a JSON column, typed, and blanks a placeholder value. |
| query.expression-help | The expression editor autocompletes and lists the available functions. |
| query.summarize | A user groups rows by a dimension and aggregates measures. |
| query.summarize-grain | A date dimension in a summarize groups at a grain, and a time column only at a clock grain. |
| query.summarize-aggregations | A measure aggregates as sum, count, average, min, max or distinct count. |
| query.summarize-currency-carried | A money measure carries its currency code beside it, hidden from column lists and exports. |
| query.order-by | A user sorts the result by a column, ascending or descending. |
| query.limit | A user caps the number of rows the query returns. |
| query.pivot-wider | A user pivots a dimension's values into columns, with the smaller values folded into Others. |
| query.custom-operation | A user adds a Python expression as a pipeline step. |
| query.sql-column | A user adds a column from a raw SQL expression written in the source's dialect. |
| query.unknown-operation-refused | A pipeline holding an operation this version does not know is refused, not silently skipped. |
| query.native-sql | A user writes native SQL against a data source and runs it. |
| query.native-sql-one-statement | Native SQL is one statement over unqualified table names; more than one statement or a schema-qualified name is refused. |
| query.native-sql-format | A user reformats the SQL text. |
| query.native-sql-schema-explorer | A user browses the source's tables and columns and inserts a name into the SQL. |
| query.native-sql-autocomplete | The SQL editor autocompletes table and column names. |
| query.script | A user writes a Python script that assigns `results` and runs it as a query. |
| query.script-variables | A user passes variables into a script, and changing one re-runs it. |
| query.script-force-run | A user re-runs a script ignoring the cached result. |
| query.script-logs | A script's prints and errors, with the failing line number, show in a log panel. |
| query.step-back | A user steps back to an earlier operation and the result rewinds to that point. |
| query.remove-operation | A user removes an operation mid-pipeline. |
| query.reopen-operation | A user reopens an operation's editor to change it. |
| query.undo-redo | A user undoes and redoes pipeline edits. |
| query.view-sql | A user opens View SQL and sees the SQL the last run executed. |
| query.rename | A user renames a query. |
| query.duplicate | A user duplicates a query in the workbook. |
| query.copy-paste | A user copies a query as JSON and pastes it into a workbook, references pointing at the new copy. |
| query.data-store-toggle | A user switches a query between the live connection and the data store. |
| query.refresh-stored-tables | An admin re-imports the data store tables a query reads. |
| query.download-results | A user downloads the result as CSV or Excel. |
| query.download-cell-is-data | A downloaded cell that looks like a spreadsheet formula opens as text, while handles, emails, phone numbers and headers are untouched. |
| query.result-find | A user searches within the result rows and columns. |
| query.result-pagination | A user pages through the result rows. |
| query.result-timing | The result pane states how long the run took, or that it came from cache. |
| query.result-cache | A re-run reads the result from the cache, with infinity and NaN read back as blanks. |
| query.result-raw-row | The raw row behind a formatted result row is the one at the same position, across re-runs. |
| query.result-drill | A user clicks a cell of a summarized result and drills into it as a chart would. |
| query.conditional-formatting | A user highlights result cells by a rule or colors them on a scale. |
| query.alerts-open | A user opens the list of alerts on a query and searches it. |

## charts

| Slug | Feature |
|---|---|
| charts.type-number | A user draws a query as a Number chart, one card per reading. |
| charts.type-bar | A user draws a query as a Bar chart. |
| charts.type-line | A user draws a query as a Line chart. |
| charts.type-row | A user draws a query as a Row chart. |
| charts.type-donut | A user draws a query as a Donut chart. |
| charts.type-funnel | A user draws a query as a Funnel chart. |
| charts.type-table | A user draws a query as a Table chart. |
| charts.type-map | A user draws a query as a Map, one value per region. |
| charts.type-bubble | A user draws a query as a Bubble chart, one measure against another. |
| charts.type-sankey | A user draws a query as a Sankey diagram. |
| charts.type-heatmap | A user draws a query as a Heatmap. |
| charts.every-type-covered | Every chart type derives its query, and a type added without a derivation is caught. |
| charts.switch-type-keeps-config | A user changes chart type and the config survives where the new type has the same slot. |
| charts.query-picker | A user picks which workbook query the chart reads. |
| charts.title | A user titles a chart. |
| charts.missing-slot-message | A half-configured chart says which slot is missing, in the words the form uses. |
| charts.preview | The builder previews an unsaved config and shows the rows and SQL that fed it. |
| charts.preview-table-sort | A user sorts the preview rows by a column. |
| charts.preview-table-grain | A user picks a date column's grain from the preview table header. |
| charts.x-axis | A user picks the dimension drawn on the x-axis; text reads as categories, a date as a timeline, a number as a quantity. |
| charts.y-axis-series | A user adds one or more measures as series. |
| charts.measure-aggregation | A user picks a measure's aggregation, then its column. |
| charts.measure-expression | A user writes a measure as a custom expression and names it. |
| charts.measure-unit | A measure prints as a plain number, a percent, or a currency read from the site or from a column. |
| charts.dimension-label | A user relabels a dimension. |
| charts.dimension-grain | A user sets a date dimension's grain and the chart groups by it. |
| charts.split-by | A user splits the series by a dimension and sees one series per value. |
| charts.split-by-max-values | A user caps how many split values are drawn; the rest fold into Others. |
| charts.tooltip-measures | A user adds measures that print in the tooltip only. |
| charts.series-type | A user draws one series as a line over bars, or as bars. |
| charts.series-align | A user measures a series against a second value axis on the right. |
| charts.series-color | A user colors a series, and a color change does not re-run the query. |
| charts.series-data-labels | A user shows value labels on one series or on the whole axis. |
| charts.axis-label | A user shows and names the y-axis label. |
| charts.axis-min-max | A user pins the y-axis scale bounds. |
| charts.bar-stack | A user stacks the bars; a chart with bars on both axes cannot stack. |
| charts.bar-normalize | A user normalizes stacked bars to shares of the whole. |
| charts.bar-overlap | A user overlaps bars instead of grouping them. |
| charts.line-smooth | A user draws a line series curved. |
| charts.line-area | A user fills the area under a line. |
| charts.line-data-points | A user shows a marker on each point of a line. |
| charts.reference-lines | A user draws a reference line at a constant or at the average, median, min, max or sum of a measure, with a label, color and dash. |
| charts.sort | A user sorts a chart by a column and flips the direction; a date axis runs forwards unless the author turns it. |
| charts.filter | A user filters a chart independently of its query. |
| charts.limit | A user caps the rows the chart's query returns. |
| charts.style-change-no-rerun | A change to labels, colors or number format redraws the chart without re-running its query; a measure or comparison change re-runs it. |
| charts.number-format | A user sets a prefix, suffix and decimals for the chart, and one measure overrides it key by key. |
| charts.number-format-shorten | A user abbreviates large numbers. |
| charts.number-format-older-spellings | A chart saved with an older format spelling prints the same as before. |
| charts.number-readings | A user adds several readings to a Number chart, each with its own settings that follow it when reordered or removed. |
| charts.number-reading-color | A user colors one reading's value. |
| charts.number-negative-is-better | A user marks a reading so that a decrease reads as an improvement. |
| charts.number-period | A user picks the period a card reads: a span the engine resolves against the clock, or a grain the card groups by. |
| charts.number-period-last-n | A user sets how many units a Last N period spans. |
| charts.number-period-include-current | A user includes the in-progress period in a card's window. |
| charts.number-date-column | A user picks the date column a card's period and sparkline read. |
| charts.number-target | A user measures a reading against a constant or a measure and the card states the gap. |
| charts.number-comparison | A user compares a reading with the previous period, the same period last year, a constant or a measure, and the card states the change. |
| charts.number-comparison-show | A user prints a comparison as a percent change or as a difference in the value's own units. |
| charts.number-comparison-caption | A user writes a caption for the comparison row. |
| charts.number-sparkline | A user draws a trend under a card, split one grain finer than its period and filtered the same way. |
| charts.donut-max-slices | A user caps the slices drawn; the rest collapse into a tail. |
| charts.donut-inline-labels | A user prints the shares on the slices instead of a legend. |
| charts.funnel-stages | A user builds a funnel from several measures, one stage each, or from a label and value column. |
| charts.table-rows-columns-values | A user lays out a Table chart as row dimensions, pivot columns and measures. |
| charts.table-max-column-values | A user caps how many pivoted columns are drawn. |
| charts.table-column-width | A user fixes a column's width. |
| charts.table-wrap-text | A user wraps long text in a column. |
| charts.table-pin-column | A user pins a column so it stays visible while scrolling. |
| charts.table-totals | A user adds a totals row or a totals column. |
| charts.table-color-scale | A user colors cells by magnitude. |
| charts.table-conditional-formatting | A user adds a formatting rule to a Table chart and it reaches the column, or every pivoted column, it names. |
| charts.table-header-sort | A user sorts a Table chart by clicking a column header, and the sort is saved to the chart; a reader sorts nothing. |
| charts.table-record-link | A Table cell that names a desk document opens its form; every other cell stays a value. |
| charts.table-loading | A Table chart's card, not its grid, veils a run in flight. |
| charts.table-renders-outside-dashboard | A Table chart draws its rows outside a dashboard. |
| charts.map-type | A user picks the world or India map. |
| charts.map-region-mapping | A user maps a region name the data uses to the name the map knows, and clicks resolve back to the rows. |
| charts.map-color-scale | A map colors regions in classes cut where the data parts. |
| charts.bubble-size-name-color | A user sizes bubbles by a measure, names them by a column and colors them by a dimension. |
| charts.bubble-data-labels | A user prints each bubble's name beside it. |
| charts.bubble-quadrants | A user cuts the bubble plot into quadrants at a value on each scale. |
| charts.sankey-source-target-value | A user picks the source, target and value columns of a Sankey; a counting value column is summed so ribbons keep their width. |
| charts.sankey-orientation-align | A user sets a Sankey's orientation and node alignment. |
| charts.heatmap-two-cuts | A user cuts a heatmap by two dimensions and colors cells by a measure; both cuts are sorted and one column cannot cut twice. |
| charts.heatmap-palette-range | A user picks a sequential or diverging palette and pins the ends of the color scale. |
| charts.heatmap-show-values | A user prints the number inside each heatmap cell. |
| charts.refresh | A user re-runs a chart's query. |
| charts.export-png | A user downloads a chart as a PNG. |
| charts.duplicate | A user duplicates a chart in the workbook. |
| charts.reset-options | A user resets a chart's config to defaults. |
| charts.view-sql | A user sees the SQL a chart's last run executed. |
| charts.copy-paste | A user copies a chart as JSON and pastes it into a workbook with its query. |
| charts.expand | A user opens a chart full-size. |
| charts.retry | A user retries a chart or a reading after a failed run. |
| charts.reset-filters | A user clears a card's own filters and the grid filters reaching it in one step. |
| charts.rename-while-saving | A user renames a chart while it saves and the newer name wins. |
| charts.drill-rows | A user clicks a segment and views the rows behind it, ranked by the clicked measure. |
| charts.drill-segment | A click on a bar, wedge, cell, flow or reading pins the segment's dimension values, and a split or pivot segment pins both its axis and its series. |
| charts.drill-date-segment | A click on a date segment covers the whole bucket the chart grouped by, and a time bucket filters by the clock. |
| charts.drill-number-card | A card's drill reads the period it states, not the comparison periods it also fetched. |
| charts.drill-breakdown | A user breaks a segment down by another column and sees a ranking, cut to the top rows with the full count stated. |
| charts.drill-breakdown-offers | The break-down menu offers the chart's other dimensions first and drops what the path already pins. |
| charts.drill-breakdown-shape | A breakdown draws itself as a row chart, a line, bars, a donut or a grid from the answer's shape, not the column type. |
| charts.drill-additive | A breakdown draws as parts of one whole only when its groups add up to the segment above. |
| charts.drill-grain | A user re-asks a breakdown level at another date grain, and a date breakdown buckets at a grain derived from the segment's span. |
| charts.drill-breadcrumbs | A user steps back to an earlier drill level through the breadcrumb trail, and a level already asked for is not fetched again. |
| charts.drill-conditional-measure | Drilling a conditional measure filters the rows by the condition the measure counted. |
| charts.drill-record-link | A drilled row names the desk document it opens. |
| charts.drill-surface-bound | A drill reaches only the columns the chart already published and never leaks the query behind it. |
| charts.drill-open-as-query | A user opens a drill level as a new query in the workbook and edits its pipeline. |
| charts.drill-rows-filter | A user adds ad-hoc filters over the drilled rows. |

## dashboard

| Slug | Feature |
|---|---|
| dashboard.loads | A dashboard loads with every chart rendered. |
| dashboard.create-add-chart | A user creates a dashboard and adds a chart to it. |
| dashboard.chart-selector | A user searches the chart list and selects all or none. |
| dashboard.drag-chart-from-sidebar | A user drags a chart from the sidebar onto the grid. |
| dashboard.move-resize | A user moves and resizes an item; the item it lands on is pushed out from under it. |
| dashboard.compact-layout | A user turns gap-closing on or off; a new dashboard closes its gaps. |
| dashboard.breakpoints | A user arranges the grid per width; a narrow grid stacks cells the author never arranged and keeps the ones they did. |
| dashboard.cell-height-rule | A Number cell takes the height its reading needs: a delta row when compared, a sparkline band when trended. |
| dashboard.number-cell-per-reading | A Number chart on a dashboard is one cell per reading, each drawing only the reading it names. |
| dashboard.filter-add | A user adds a dashboard filter with a label and a type. |
| dashboard.filter-links | A user links a dashboard filter to a chart's column and the chart refilters; an unlinked chart is left alone. |
| dashboard.filter-values | A dashboard filter offers the distinct values, or the number range, of the column it links. |
| dashboard.filter-default | A user sets a filter's default operator and value. |
| dashboard.filter-icon | A user picks an icon for a filter's trigger. |
| dashboard.filter-clear | A reader clears a dashboard filter's value. |
| dashboard.text-block | A user adds a text block and its rich text is saved safe to render. |
| dashboard.remove-item | A user removes an item from the dashboard. |
| dashboard.reset-layout | A user discards unsaved layout changes. |
| dashboard.rename | A user renames a dashboard. |
| dashboard.refresh | A reader reloads a dashboard's chart data, with or without the cache. |
| dashboard.export-png | A user downloads a dashboard as a PNG. |
| dashboard.card-filter | A reader narrows one card with its own filter, and the filter offers only what the card draws. |
| dashboard.card-find | A reader searches a table card's drawn rows. |
| dashboard.drill | A reader drills from a dashboard card under the dashboard's filters. |
| dashboard.edit-chart | A reader with access jumps from a card to the chart in its workbook. |
| dashboard.list | A user browses dashboards, searches by title and switches between all, recent, favorite, created and shared. |
| dashboard.favorite | A user marks a dashboard as a favorite. |
| dashboard.preview-image | A dashboard card shows a preview image, generated by a browser that opens only that dashboard with a one-time key. |
| dashboard.open-workbook | A reader with access opens the dashboard's workbook. |

## workbook

| Slug | Feature |
|---|---|
| workbook.create | A user creates a workbook from the list or the home page. |
| workbook.open-tabs | A user opens a workbook and switches between its query, chart and dashboard tabs. |
| workbook.rename | A user renames a workbook. |
| workbook.save | A workbook saves and survives a reload. |
| workbook.delete | A user deletes a workbook and its queries, charts and dashboards go with it. |
| workbook.add-items | A user adds a query, a chart on the active query, or a dashboard from the sidebar. |
| workbook.remove-item | A user removes a query, chart or dashboard from the sidebar. |
| workbook.folders | A user creates, renames and removes folders and moves items into them. |
| workbook.reorder | A user reorders items and folders by dragging, and a stale item in the order is skipped. |
| workbook.duplicate | A user duplicates a workbook into an independent copy with the same folders. |
| workbook.copy-paste | A user copies a workbook as JSON and pastes it as a new workbook, every reference pointing at the new copies. |
| workbook.lineage | A user views the table-to-query lineage graph and jumps to a query from it. |
| workbook.list | A user searches workbooks by title, switches between all, created and shared, and loads more. |
| workbook.home-recent | The home page lists recent workbooks. |
| workbook.open-in-desk | An admin opens a workbook, chart or query in Desk. |
| workbook.read-only-shield | A viewer sees the workbook marked read-only. |

## shared

| Slug | Feature |
|---|---|
| shared.dashboard-link | A user publishes a dashboard and a logged-out visitor opens the link and sees its charts. |
| shared.chart-link | A user publishes a chart and a logged-out visitor opens the link. |
| shared.revoke | A revoked public link stops working. |
| shared.copy-link-embed | A user copies the public link or an iframe embed snippet. |
| shared.rows-are-the-publishers | A visitor on a public link sees the rows the publisher can see, never more, and the session stays Guest. |
| shared.publish-needs-share | Only a user with share access can publish, and a plain save cannot publish or name whose rows a link reads. |
| shared.chart-on-public-dashboard | An unpublished chart on a public dashboard is readable through that dashboard and runs as its publisher; two dashboards pick the older. |
| shared.public-methods-bounded | A public link can call only the read methods it needs, with builder-only arguments stripped, and never a download. |
| shared.filters-on-public-dashboard | A visitor uses the dashboard's filters and card filters, routed by the published dashboard's own links. |
| shared.old-name-resolves | A link to a renamed public dashboard or chart still opens it; a private one gives nothing away. |
| shared.currency-for-guest | A visitor sees amounts in the site's currency symbol. |
| shared.read-once | Several cards drawing one chart under the same filters ask the server once. |

## data-source

| Slug | Feature |
|---|---|
| data-source.connect-mariadb | A user connects a MariaDB database with host, port, database, username and password. |
| data-source.connect-postgres | A user connects a PostgreSQL database, naming a schema. |
| data-source.connect-clickhouse | A user connects a ClickHouse database. |
| data-source.connect-duckdb | A user connects a DuckDB file by URL. |
| data-source.test-connection | A user tests a new connection before adding it and the result reports. |
| data-source.ssl | A user encrypts a connection, and a CA certificate turns encryption into verification. |
| data-source.connection-error-detail | A failed connection tells everyone it failed and only whoever may edit the source why. |
| data-source.credentials-stay-with-admins | A data source's credentials never reach a non-admin, while its title stays readable. |
| data-source.upload-file | A user uploads a CSV, Excel or JSON file and it becomes a queryable table. |
| data-source.upload-table-name | A user names the table an upload becomes and can reset the file. |
| data-source.list | A user browses data sources and searches them by title. |
| data-source.table-list | A user browses a data source's tables and searches them by name. |
| data-source.table-preview | A user previews a table's first rows, columns and row count, seeing only rows they may read. |
| data-source.update-tables | A user re-syncs the table list; a re-spelled table is renamed, not duplicated, and every referrer follows. |
| data-source.table-links | A Frappe site source infers table links between its tables to suggest joins. |
| data-source.postgres-schema | A Postgres table name carries its schema only while the source reads several schemas. |
| data-source.table-label-is-text | A table label renders as text in Desk, never as markup. |
| data-source.table-stats | A table's stats name only the queries the caller may read and the newest completed import. |

## permissions

| Slug | Feature |
|---|---|
| permissions.viewer-sees-granted | A viewer sees only the workbooks granted to them, and loses one when its share is removed. |
| permissions.viewer-cannot-edit | A viewer cannot edit a workbook they can read, nor add folders or reorder its items. |
| permissions.share-workbook-user | A user shares a workbook with another user as viewer or editor, or removes them. |
| permissions.share-workbook-org | A user opens a workbook to the whole organization as view or edit. |
| permissions.share-user-lookup | The share dialog finds users by name or email and shows nothing but directory fields; an admin can turn lookup off. |
| permissions.share-dashboard | A user grants a dashboard to specific people or the organization, and access grants read but not write. |
| permissions.chart-access-follows | A chart is readable through its own share, its workbook, or a dashboard it sits on, and its query through the chart. |
| permissions.team-grant | An admin creates a team, adds members and grants it data sources and tables; the grant reaches that team only. |
| permissions.team-off-open | With team permissions off, every Insights user sees every data source and table, and grants are inert. |
| permissions.no-source-access-no-query | A user without access to a data source cannot query it. |
| permissions.table-row-restriction | An admin restricts which rows of a table a team sees with an expression. |
| permissions.admin-bypass | An admin sees every data source and table whatever the grants say. |
| permissions.non-insights-user | A user without an Insights role reads nothing and calls no endpoint. |
| permissions.download-gated | A download needs the role's export permission, access to the query, and the site-wide download toggle. |
| permissions.chart-cannot-link-unreadable-query | A chart cannot name, or be repointed to, a query its author cannot read. |
| permissions.dashboard-cannot-hold-unreadable-chart | A dashboard cannot hold a chart its author cannot read. |
| permissions.query-reference-checked | A query cannot source a query its author cannot read, saved or sent inline. |
| permissions.request-body-not-trusted | Access is decided against the stored document, never against claims in the request. |
| permissions.authoring-needs-seat | Only a user with an authoring seat previews or drills an unsaved config, and only over queries they can read. |
| permissions.site-user-permissions | A site-database source applies the user's desk row and column permissions to what a query returns. |
| permissions.import-without-access | A user imports a workbook, query or chart file without access to the originals it was exported from. |
| permissions.malformed-request-refused | A request with a wrongly typed argument is refused with a message, not a crash. |
| permissions.search-respects-access | A search over workbooks and columns returns only what the caller may read. |

## data-store

| Slug | Feature |
|---|---|
| data-store.import-table | An admin imports a source table into the data store and queries run against the copy. |
| data-store.import-row-limit | An admin caps how many rows an import copies. |
| data-store.list | An admin browses the stored tables and searches them by name. |
| data-store.import-cursor | An incremental import's cursor describes what is in the store, not what a run intended. |
| data-store.failed-import-notice | A reader is told when a table's newest import failed, and nothing while one runs or a retry is queued. |
| data-store.write-lock | A write waits for readers to finish and gives up at a timeout. |
| data-store.division-by-zero | A division by zero returns null in the data store, as it does on the live connection. |
| data-store.cleanup-prunes-stale | The weekly cleanup drops a table no query has used, and keeps one used recently, nested, freshly imported or incremental. |
| data-store.cleanup-keeps-unexplained | The cleanup deletes only what it can rebuild and keeps an unexplained orphan. |
| data-store.compaction | The store file is compacted without losing data, and small files are left alone. |

## alerts

| Slug | Feature |
|---|---|
| alerts.create | A user creates an alert on a query with a name and a schedule. |
| alerts.condition | A user sets the condition, from the builder or as a custom expression, that triggers the alert. |
| alerts.message | A user writes the alert's message with field tokens. |
| alerts.email | An alert emails its recipients, inside or outside the site, with a reply-to that reaches the author and a body that names the alert and the site as text. |
| alerts.webhook | An alert posts a versioned payload to a webhook, token in the header, rows capped and the cap declared. |
| alerts.webhook-address-policy | A webhook reaches only a public https address, never a private or loopback one, even through rebinding or a proxy. |
| alerts.telegram | An alert sends to Telegram. |
| alerts.test-send | A user sends an alert once as a test. |
| alerts.enable | A user enables or disables an alert, and the alert runs with the rows of whoever enabled it. |
| alerts.failed-run-recorded | A failed delivery records its run so it is not retried every tick. |

## templates

| Slug | Feature |
|---|---|
| templates.library | A user browses the library of templates the installed apps ship, hidden where a required app is missing. |
| templates.import | An admin imports a template as one Administrator-owned copy shared read-only with the organization, once per site. |
| templates.open | A user opens the imported workbook from the library, or through a template link. |
| templates.update | An admin updates an imported copy to a newer shipped version, replacing their changes after a confirm. |
| templates.auto-update-pristine | A copy nobody edited follows a newer version on migrate; an edited copy is left for a manual update. |
| templates.shipped-are-valid | Every shipped template imports cleanly and its money measures name a currency column. |

## settings

| Slug | Feature |
|---|---|
| settings.profile | A user edits their first and last name. |
| settings.week-start | An admin sets the weekday the week starts on and week ranges follow it. |
| settings.fiscal-year-start | An admin sets the fiscal year start and fiscal year ranges follow it. |
| settings.demo-data | An admin sets up demo data and a demo workbook. |
| settings.demo-banner-dismiss | A user dismisses the demo data banner and it stays hidden. |
| settings.invite-users | An admin invites users by email; the link carries a key stored only hashed, and accepting signs in only a new account. |
| settings.users-list | An admin searches the user list by name or email. |
| settings.permissions-toggle | An admin turns team-based permissions on. |
| settings.apply-user-permissions | An admin applies site role and user permissions to the site source. |
| settings.allow-download | An admin allows or blocks downloads site-wide. |
| settings.team-manage | An admin renames a team, adds and removes members, and deletes it; the Admin team cannot be renamed or deleted. |
| settings.data-store-enable | An admin enables the data store and sets its row and memory limits. |
| settings.color-scheme | A user switches between light and dark mode. |
| settings.log-out | A user logs out after a confirm. |
| settings.login | A user logs in with email and password and sees an error on failure. |
| settings.translations | The UI shows in the user's language. |

## upgrade

| Slug | Feature |
|---|---|
| upgrade.number-older-shapes | A Number chart saved before periods and per-reading comparisons existed reads the same as it did. |
| upgrade.cached-queries-removed | The query documents charts once cached their query in are removed, unless something still reads them. |
| upgrade.older-grid-read | A dashboard arranged before the grid row changed keeps the pixels it covered. |
| upgrade.older-export-imports | A workbook exported before names became strings still imports. |

## tooling

| Slug | Feature |
|---|---|
| tooling.workbook-skill-verify | The workbook skill's verify step reads a chart config the way the app does, so an agent authoring over the API is told what it got wrong. |
| tooling.feature-coverage | The coverage table is generated from the `@feature` directives on the tests, and CI fails when a test has none or names a slug the feature list does not. |
| tooling.e2e-seeding | An e2e test gets a seeded workbook, chart and viewer over REST before the browser opens. |
