import { FIELDTYPES, safeJSONParse } from '@/utils'
import { getFormattedDate } from '../format'

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

export function getFormattedResult(data) {
	if (!data || !data.length) return []

	const columns = data[0]
	const columnTypes = data[0].map((c) => c.type)

	return data.map((row, index) => {
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
				const formatOption = columns[idx]?.options
				if (formatOption) {
					cell = applyColumnFormatOption(safeJSONParse(formatOption), cell)
				}
			}
			return cell
		})
	})
}
