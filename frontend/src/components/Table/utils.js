import { ellipsis, formatNumber } from '@/utils'
import { Badge } from 'frappe-ui'
import { defineAsyncComponent, h } from 'vue'

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

export function getCellComponent(cell, column) {
	const value = cell.getValue()

	const parsedPills = parsePills(value)
	if (parsedPills) {
		return h(
			'div',
			parsedPills.map((item) => h(Badge, { label: item }))
		)
	}

	if (column.column_options.column_type == 'Link') {
		const comp = defineAsyncComponent(() => import('@/components/Table/TableLinkCell.vue'))
		return h(comp, {
			label: value,
			url: column.column_options.link_url.replace('{{value}}', value),
		})
	}

	if (column.column_options.column_type == 'Number') {
		const comp = defineAsyncComponent(() => import('@/components/Table/TableNumberCell.vue'))
		const allValues = cell.table
			.getCoreRowModel()
			.rows.map((r) => r.getValue(column.column || column.label))
		return h(comp, {
			value: value,
			prefix: column.column_options.prefix,
			suffix: column.column_options.suffix,
			decimals: column.column_options.decimals,
			minValue: Math.min(...allValues),
			maxValue: Math.max(...allValues),
			showInlineBarChart: column.column_options.show_inline_bar_chart,
		})
	}

	const isNumber = typeof value == 'number'
	return h('div', { class: isNumber ? 'text-right tnum' : '' }, value)
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
