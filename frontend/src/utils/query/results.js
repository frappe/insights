import { computed } from 'vue'
import { safeJSONParse } from '@/utils'
import { FIELDTYPES } from '@/utils/query'

export function useQueryResults(query) {
	const maxRows = 1000
	const data = computed(() => {
		return safeJSONParse(query.doc.result, []).slice(0, maxRows)
	})
	const formattedData = computed(() => {
		return data.value?.map((row) => {
			return row.map((cell, idx) => {
				const column = query.columns.data[idx] || {}
				if (FIELDTYPES.NUMBER.includes(column.type)) {
					cell = Number(cell).toLocaleString()
				}
				if (column.format_option) {
					cell = applyColumnFormatOption(column, cell)
				}
				return cell
			})
		})
	})

	function getColumnValues(column) {
		const columnIdx = query.columns.data.findIndex((c) => c.column === column)
		if (columnIdx > -1) {
			return data.value.map((row) => row[columnIdx])
		}
	}

	return {
		data,
		formattedData,
		getColumnValues,
	}
}

function applyColumnFormatOption(column, cell) {
	if (column.format_option.prefix) {
		return `${column.format_option.prefix} ${cell}`
	}
	if (column.format_option.suffix) {
		return `${cell} ${column.format_option.suffix}`
	}
	return cell
}

function formatCells() {
	return this.data.map((row) => {
		return row.map((cell, idx) => {
			const column = this.columns[idx]
			if (!column) {
				return cell
			}
			if (FIELDTYPES.NUMBER.includes(column.type)) {
				cell = Number(cell).toLocaleString()
			}
			if (column.format_option) {
				cell = this.applyColumnFormatOption(column, cell)
			}
			return cell
		})
	})
}
