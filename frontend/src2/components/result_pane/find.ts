import type { QueryResultColumn, QueryResultRow } from '../../types/query.types'

// Find is client-only: it narrows the rows already loaded and never asks the
// server for more. One term does two jobs — it keeps rows and it lists columns.

/** The rows a term keeps: case-insensitive substring, any column. */
export function findRows(rows: QueryResultRow[], term: string): QueryResultRow[] {
	const needle = term.trim().toLowerCase()
	if (!needle) return rows
	return rows.filter((row) =>
		Object.values(row).some((value) =>
			String(value ?? '')
				.toLowerCase()
				.includes(needle),
		),
	)
}

/** The columns a term names, in result order. Empty term matches nothing. */
export function findColumns(columns: QueryResultColumn[], term: string): QueryResultColumn[] {
	const needle = term.trim().toLowerCase()
	if (!needle) return []
	return columns.filter((column) => column.name.toLowerCase().includes(needle))
}
