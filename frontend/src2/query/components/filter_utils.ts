import { FIELDTYPES, FilterType } from '../../helpers/constants'
import { __ } from '../../translation'
import {
	ColumnDataType,
	FilterExpression,
	FilterOperator,
	FilterRule,
	Preset,
} from '../../types/query.types'
import dayjs from '../../helpers/dayjs'
import { formatDateRangeDescription } from './formatting_utils'

export function getOperatorOptions(filterType: FilterType) {
	const options = [] as { label: string; value: FilterOperator }[]
	if (filterType === 'String') {
		options.push({ label: __('is'), value: 'in' }) // value selector
		options.push({ label: __('is not'), value: 'not_in' }) // value selector
		options.push({ label: __('contains'), value: 'contains' }) // text
		options.push({ label: __('does not contain'), value: 'not_contains' }) // text
		options.push({ label: __('starts with'), value: 'starts_with' }) // text
		options.push({ label: __('ends with'), value: 'ends_with' }) // text
		options.push({ label: __('is set'), value: 'is_set' }) // no value
		options.push({ label: __('is not set'), value: 'is_not_set' }) // no value
	}
	if (filterType === 'Number') {
		options.push({ label: __('equals'), value: '=' })
		options.push({ label: __('not equals'), value: '!=' })
		options.push({ label: __('greater than'), value: '>' })
		options.push({ label: __('greater than or equals'), value: '>=' })
		options.push({ label: __('less than'), value: '<' })
		options.push({ label: __('less than or equals'), value: '<=' })
		options.push({ label: __('between'), value: 'between' })
		options.push({ label: __('is set'), value: 'is_set' })
		options.push({ label: __('is not set'), value: 'is_not_set' })
	}
	if (filterType === 'Date') {
		options.push({ label: __('between'), value: 'between' })
		options.push({ label: __('equals'), value: '=' })
		options.push({ label: __('not equals'), value: '!=' })
		options.push({ label: __('greater than'), value: '>' })
		options.push({ label: __('greater than or equals'), value: '>=' })
		options.push({ label: __('less than'), value: '<' })
		options.push({ label: __('less than or equals'), value: '<=' })
		options.push({ label: __('within'), value: 'within' })
		options.push({ label: __('is set'), value: 'is_set' })
		options.push({ label: __('is not set'), value: 'is_not_set' })
	}
	return options
}

export function getValueSelectorType(operator: FilterOperator, filterType: FilterType) {
	if (['is_set', 'is_not_set'].includes(operator)) return

	if (filterType === 'String') {
		return ['in', 'not_in'].includes(operator) ? 'select' : 'text'
	}
	if (filterType === 'Number') {
		return operator === 'between' ? 'text' : 'number'
	}
	if (filterType === 'Date') {
		return operator === 'between' ? 'date_range' : operator === 'within' ? 'relative_date' : 'date'
	}
	return 'text'
}

export function isFilterExpressionValid(filter: FilterExpression) {
	return filter.expression.expression.trim().length > 0
}

export function getFilterType(columnType: ColumnDataType): FilterType {
	if (FIELDTYPES.TEXT.includes(columnType)) return 'String'
	if (FIELDTYPES.NUMBER.includes(columnType)) return 'Number'
	if (FIELDTYPES.DATE.includes(columnType)) return 'Date'
	return 'String'
}

export function isFilterValid(filter: FilterRule, filterType: FilterType) {
	if (!filter.column.column_name || !filter.operator) {
		return false
	}
	if (!filter.column.column_name || !filter.operator) {
		return false
	}

	const valueSelectorType = getValueSelectorType(filter.operator, filterType)

	// if selector type is none, no need to validate
	if (!valueSelectorType) {
		return true
	}

	if (!filter.value && filter.value !== 0) {
		return false
	}

	// for number, validate if it's a number
	if (filterType === 'Number') {
		if (filter.operator === 'between') {
			return (
				Array.isArray(filter.value) &&
				filter.value.length === 2 &&
				filter.value.every(isValidNumber)
			)
		}
		return isValidNumber(filter.value)
	}

	// for text,
	// if it's a select, validate if it's an array of strings
	// if it's a text, validate if it's a string
	if (filterType === 'String') {
		if (valueSelectorType === 'select') {
			return Boolean(
				Array.isArray(filter.value) &&
					filter.value.length &&
					filter.value.every((v: any) => typeof v === 'string')
			)
		} else {
			return typeof filter.value === 'string'
		}
	}

	// for date,
	// if it's a date, validate if it's a date string
	// if it's a date range, validate if it's an array of 2 date strings
	if (filterType === 'Date') {
		if (valueSelectorType === 'date' || valueSelectorType === 'relative_date') {
			return typeof filter.value === 'string'
		} else if (valueSelectorType === 'date_range') {
			return Boolean(
				Array.isArray(filter.value) &&
					filter.value.length === 2 &&
					filter.value.every((v: any) => typeof v === 'string')
			)
		}
	}

	return false
}

export function isValidNumber(value: any) {
	const invalidNaNs = [null, undefined, '']
	return (
		!isNaN(value) &&
		!invalidNaNs.includes(value) &&
		typeof value !== 'boolean' &&
		!isNaN(parseFloat(value))
	)
}

// dateRangePicker string/array conversion
export function normalizeDateRange(val: any) {
	if (typeof val === 'string') {
		return val.split(',')
	}
	return val
}

export function getDatePresets(operator: FilterOperator) {
	const presets: Preset[] = []
	if (operator === 'within') {
		presets.push({ label: __('Today'), value: () => 'Current Day' })
		presets.push({ label: __('This Week'), value: () => 'Current Week' })
		presets.push({ label: __('This Month'), value: () => 'Current Month' })
		presets.push({ label: __('Last 7 Days'), value: () => 'Last 7 Day' })
		presets.push({ label: __('Last 30 Days'), value: () => 'Last 30 Day' })
		presets.push({ label: __('Last 3 Months'), value: () => 'Last 3 Month' })
		presets.push({ label: __('Last Year'), value: () => 'Last 1 Year' })
	}
	if (operator === 'between') {
		const format = 'YYYY-MM-DD'
		const d = {
			today: () => dayjs(),
			yesterday: () => dayjs().subtract(1, 'day'),
			monthStart: () => dayjs().startOf('month'),
			monthEnd: () => dayjs().endOf('month'),
			lastMonthStart: () => dayjs().subtract(1, 'month').startOf('month'),
			lastMonthEnd: () => dayjs().subtract(1, 'month').endOf('month'),
			quarterStart: () => dayjs().startOf('quarter'),
			quarterEnd: () => dayjs().endOf('quarter'),
			lastYearStart: () => dayjs().subtract(1, 'year').startOf('year'),
			lastYearEnd: () => dayjs().subtract(1, 'year').endOf('year'),
		}
		presets.push({
			label: __('Today'),
			value: () => [d.today().format(format), d.today().format(format)],
			description: () => formatDateRangeDescription(d.today()),
		})
		presets.push({
			label: __('Yesterday'),
			value: () => [d.yesterday().format(format), d.yesterday().format(format)],
			description: () => formatDateRangeDescription(d.yesterday()),
		})
		presets.push({
			label: __('This Month'),
			value: () => [d.monthStart().format(format), d.monthEnd().format(format)],
			description: () => formatDateRangeDescription(d.monthStart(), d.monthEnd()),
		})
		presets.push({
			label: __('Last Month'),
			value: () => [d.lastMonthStart().format(format), d.lastMonthEnd().format(format)],
			description: () => formatDateRangeDescription(d.lastMonthStart(), d.lastMonthEnd()),
		})
		presets.push({
			label: __('This Quarter'),
			value: () => [d.quarterStart().format(format), d.quarterEnd().format(format)],
			description: () => formatDateRangeDescription(d.quarterStart(), d.quarterEnd()),
		})
		presets.push({
			label: __('Last Year'),
			value: () => [d.lastYearStart().format(format), d.lastYearEnd().format(format)],
			description: () => formatDateRangeDescription(d.lastYearStart(), d.lastYearEnd()),
		})
	}
	return presets
}

export function isPresetValueMatch(val1: any, val2: any): boolean {
	if (!val1 && !val2) return true
	if (!val1 || !val2) return false
	const a1 = normalizeDateRange(val1)
	const a2 = normalizeDateRange(val2)
	if (Array.isArray(a1) && Array.isArray(a2)) {
		return a1.length === a2.length && a1.every((v, i) => v === a2[i])
	}
	return a1 === a2
}

export function findPresetByValue(presets: Preset[], value: any): Preset | undefined {
	return presets.find(p => isPresetValueMatch(p.value(), value))
}
