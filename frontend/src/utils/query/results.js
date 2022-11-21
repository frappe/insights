import { computed, unref } from 'vue'
import { safeJSONParse } from '@/utils'
import { FIELDTYPES } from '@/utils'
import { getFormattedDate } from '../format'

export function useQueryResults(query) {
	const maxRows = 1000
	const data = computed(() => {
		return safeJSONParse(query.doc.result, []).slice(0, maxRows)
	})
	const columns = computed(() => query.columns.data)
	const formattedResult = getFormattedResult(data, columns)

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

function applyColumnFormatOption(formatOption, cell) {
	if (!formatOption) return cell
	if (formatOption.prefix) {
		return `${formatOption.prefix} ${cell}`
	}
	if (formatOption.suffix) {
		return `${cell} ${formatOption.suffix}`
	}
	if (formatOption.date_format) {
		return getFormattedDate(cell, formatOption.date_format)
	}
	return cell
}

export function getFormattedResult(data, columns) {
	return computed(() => {
		const _data = unref(data)
		const _columns = unref(columns)

		if (!_data || !_data.length) return []

		const columnTypes = _data[0].map((c) => c.split('::')[1])

		return _data.map((row, index) => {
			if (index == 0) return row // header row
			return row.map((cell, idx) => {
				const columnType = columnTypes[idx]
				if (FIELDTYPES.NUMBER.includes(columnType)) {
					if (columnType == 'Integer') {
						cell = parseInt(cell)
						cell = isNaN(cell) ? 0 : cell
					}
					if (columnType == 'Decimal') {
						cell = parseFloat(cell)
						cell = isNaN(cell) ? 0 : cell
					}
				}
				if (FIELDTYPES.DATE.includes(columnType)) {
					// only use format options for dates
					const formatOption = _columns[idx]?.format_option
					if (formatOption) {
						cell = applyColumnFormatOption(safeJSONParse(formatOption), cell)
					}
				}
				return cell
			})
		})
	})
}
