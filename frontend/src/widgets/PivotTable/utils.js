import { getFormattedCell } from '@/components/Table/utils'
import { formatNumber } from '@/utils'
import { createColumnHelper } from '@tanstack/vue-table'
// pivot data based on columns and values
export function pivotData(data, indexes = [], columns = [], values = []) {
	if (!data?.length || !(indexes.length + columns.length + values.length)) return []

	const rows = {}
	// go through each row and apply pivot logic
	for (const row of data) {
		const idx = indexes.map((k) => row[k] ?? '').join('___')
		if (!rows[idx]) {
			rows[idx] = Object.fromEntries(indexes.map((k) => [k, row[k]]))
		}
		const pivotRow = rows[idx]

		// covers flatten_column_keys (value name last, ___ separator)
		// if we pivot by "Category" and "Sub-category" and then at "Sales" this joins them into a single string
		// Electronics___Smartphones___Sales
		const colParts = columns.map((k) => row[k]).filter((v) => v != null && v !== '')
		for (const valCol of values) {
			// move value name to last position
			const flatKey = [...colParts, valCol].join('___')
			const num = Number(row[valCol])
			// group by index and sum values
			pivotRow[flatKey] = (pivotRow[flatKey] || 0) + (Number.isFinite(num) ? num : 1)
		}
	}
	// fill missing column with 0
	const pivotedRows = Object.values(rows)
	const allKeys = new Set(pivotedRows.flatMap(Object.keys))
	for (const row of pivotedRows) {
		for (const key of allKeys) {
			if (!(key in row)) row[key] = 0
		}
	}
	return pivotedRows
}

/**
 * A recursive function to convert a flat dict to a nested dict
 * Input: {
 * 	"Date": "2018-01-01",
 * 	"OK___No___Price": 100,
 * 	"OK___No___Quantity": 10,
 * 	...
 * }
 *
 * Output: {
 * 	"Date": "2018-01-01",
 * 	"OK": {
 * 		"No": {
 * 			"Price": 100,
 * 			"Quantity": 10
 * 		}
 * 	}
 * }
 */
export function convertToNestedObject(pivotedRow, seperator = '___') {
	if (!pivotedRow) return {}

	const new_obj = {}
	for (const key in pivotedRow) {
		if (!key.includes(seperator)) {
			new_obj[key] = pivotedRow[key]
			continue
		}

		const [new_key, ...rest] = key.split(seperator)
		new_obj[new_key] = new_obj[new_key] || {}
		const rest_key = rest.join(seperator)
		new_obj[new_key][rest_key] = pivotedRow[key]
	}
	for (const key in new_obj) {
		if (typeof new_obj[key] === 'object') {
			new_obj[key] = convertToNestedObject(new_obj[key])
		}
	}
	return new_obj
}

/**
 * A recursive function to convert a nested dict to a tanstack column
 * Input: {
 * 	"Date": "2018-01-01",
 * 	"OK": {
 * 		"No": {
 * 			"Price": 100,
 * 			"Quantity": 10
 * 		}
 * 	}
 * }
 *
 * Output: [
 * 	{ header: "Date", id: "Date" },
 * 	{ header: "OK", children: [
 * 		{ header: "No", children: [
 * 			{ header: "Price", id: "OK___No___Price" },
 * 			{ header: "Quantity", id: "OK___No___Quantity" }
 * 		]}
 * 	]}
 * ]
 */

export function convertToTanstackColumns(pivotedRow, idPrefix = '', seperator = '___') {
	const columnHelper = createColumnHelper()
	return _convertToTanstackColumns(columnHelper, pivotedRow, idPrefix, seperator)
}

function _convertToTanstackColumns(columnHelper, pivotedRow, idPrefix = '', seperator = '___') {
	const columns = []
	for (const key in pivotedRow) {
		if (typeof pivotedRow[key] === 'object') {
			const children = _convertToTanstackColumns(
				columnHelper,
				pivotedRow[key],
				idPrefix + key + seperator
			)
			columns.push(columnHelper.group({ header: key, columns: children }))
		} else {
			const valueIsNumber = typeof pivotedRow[key] === 'number'
			columns.push(
				columnHelper.accessor(idPrefix + key, {
					header: key,
					isNumber: valueIsNumber,
					filterFn: 'filterFunction',
					cell: (props) =>
						valueIsNumber && props.getValue() == 0
							? ''
							: getFormattedCell(props.getValue()),
					footer: (props) => {
						if (!valueIsNumber) return ''
						const filteredRows = props.table.getFilteredRowModel().rows
						const values = filteredRows.map((row) => row.getValue(idPrefix + key))
						return formatNumber(
							values.reduce((acc, curr) => acc + curr, 0),
							2
						)
					},
				})
			)
		}
	}
	return columns
}
