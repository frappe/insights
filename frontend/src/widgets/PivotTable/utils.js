import { createColumnHelper } from '@tanstack/vue-table'
import { getFormattedCell } from '@/components/Table/utils'
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
					cell: (props) =>
						valueIsNumber && props.getValue() == 0
							? ''
							: getFormattedCell(props.getValue()),
				})
			)
		}
	}
	return columns
}
