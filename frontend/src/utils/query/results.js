import { computed, unref } from 'vue'
import { safeJSONParse } from '@/utils'
import { FIELDTYPES } from '@/utils'
import { getFormattedDate } from '../format'

export function useQueryResults(query) {
	const maxRows = 1000
	const data = computed(() => {
		return safeJSONParse(query.doc.result, []).slice(0, maxRows)
	})
	const formattedResult = getFormattedResult(data, query.columns.data)

	function getColumnValues(column) {
		const columnIdx = query.columns.data.findIndex((c) =>
			c.is_expression ? c.label === column : c.column === column
		)
		if (columnIdx > -1) {
			return data.value.map((row) => row[columnIdx])
		}
	}

	function getRows(...columns) {
		const columnIndexes = columns.map((c) =>
			query.columns.data.findIndex((col) =>
				col.is_expression ? col.label === c : col.column === c
			)
		)
		return data.value.map((row) => columnIndexes.map((idx) => row[idx]))
	}

	return {
		data,
		formattedResult,
		getColumnValues,
		getRows,
	}
}

function applyColumnFormatOption(column, cell) {
	if (column.format_option.prefix) {
		return `${column.format_option.prefix} ${cell}`
	}
	if (column.format_option.suffix) {
		return `${cell} ${column.format_option.suffix}`
	}
	if (column.format_option.date_format) {
		return getFormattedDate(cell, column.format_option.date_format)
	}
	return cell
}

export function getFormattedResult(data, columns) {
	return computed(() => {
		const _data = unref(data)
		const _columns = unref(columns)

		if (!_data || _data.length == 0) return []

		return _data.map((row, index) => {
			if (index == 0) return row // header row
			return row.map((cell, idx) => {
				const column = _columns[idx] || {}
				if (FIELDTYPES.NUMBER.includes(column.type)) {
					if (column.type == 'Integer') {
						cell = parseInt(cell)
					}
					if (column.type == 'Decimal') {
						cell = parseFloat(cell)
					}
				}
				if (column.format_option) {
					cell = applyColumnFormatOption(column, cell)
				}
				return cell
			})
		})
	})
}
