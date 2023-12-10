import { ellipsis, formatNumber } from '@/utils'
import { Badge } from 'frappe-ui'
import { h } from 'vue'

export function filterFunction(row, columnId, filterValue) {
	const column = columnId
	const value = row.getValue(column)
	const isNumber = row.getVisibleCells().find((cell) => cell.column.id == column)?.column
		.columnDef.isNumber
	if (isNumber) {
		// check for an operator in the filter value: >, <, >=, <=, =, !=
		const operator = ['>=', '<=', '!=', '=', '>', '<'].find((op) => filterValue.startsWith(op))
		if (operator) {
			const filterValueNumber = Number(filterValue.replace(operator, ''))
			switch (operator) {
				case '>':
					return Number(value) > filterValueNumber
				case '<':
					return Number(value) < filterValueNumber
				case '>=':
					return Number(value) >= filterValueNumber
				case '<=':
					return Number(value) <= filterValueNumber
				case '=':
					return Number(value) == filterValueNumber
				case '!=':
					return Number(value) != filterValueNumber
			}
		}
		// check for a range in the filter value: 1-10
		const data = filterValue.match(/(\d+)-(\d+)/)
		if (data) {
			const [min, max] = data.slice(1)
			return Number(value) >= Number(min) && Number(value) <= Number(max)
		}
	}
	return String(value).toLowerCase().includes(filterValue.toLowerCase())
}

export function getFormattedCell(cell) {
	const parsedPills = parsePills(cell)
	if (parsedPills) {
		return h(
			'div',
			parsedPills.map((item) => h(Badge, { label: item }))
		)
	}
	const isNumber = typeof cell == 'number'
	const cellValue = isNumber ? formatNumber(cell) : ellipsis(cell, 100)
	return h('div', { class: isNumber ? 'text-right tnum' : '' }, cellValue)
}
function parsePills(cell) {
	try {
		const parsedPills = JSON.parse(cell)
		if (Array.isArray(parsedPills) && parsedPills.length) {
			return parsedPills
		}
	} catch (e) {
		return undefined
	}
}
