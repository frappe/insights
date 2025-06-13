import { FIELDTYPES, FilterType } from '../../helpers/constants'
import {
	ColumnDataType,
	FilterExpression,
	FilterOperator,
	FilterRule,
} from '../../types/query.types'

export function getOperatorOptions(filterType: FilterType) {
	const options = [] as { label: string; value: FilterOperator }[]
	if (filterType === 'String') {
		options.push({ label: 'is', value: 'in' }) // value selector
		options.push({ label: 'is not', value: 'not_in' }) // value selector
		options.push({ label: 'contains', value: 'contains' }) // text
		options.push({ label: 'does not contain', value: 'not_contains' }) // text
		options.push({ label: 'starts with', value: 'starts_with' }) // text
		options.push({ label: 'ends with', value: 'ends_with' }) // text
		options.push({ label: 'is set', value: 'is_set' }) // no value
		options.push({ label: 'is not set', value: 'is_not_set' }) // no value
	}
	if (filterType === 'Number') {
		options.push({ label: 'equals', value: '=' })
		options.push({ label: 'not equals', value: '!=' })
		options.push({ label: 'greater than', value: '>' })
		options.push({ label: 'greater than or equals', value: '>=' })
		options.push({ label: 'less than', value: '<' })
		options.push({ label: 'less than or equals', value: '<=' })
		options.push({ label: 'between', value: 'between' })
		options.push({ label: 'is set', value: 'is_set' })
		options.push({ label: 'is not set', value: 'is_not_set' })
	}
	if (filterType === 'Date') {
		options.push({ label: 'equals', value: '=' })
		options.push({ label: 'not equals', value: '!=' })
		options.push({ label: 'greater than', value: '>' })
		options.push({ label: 'greater than or equals', value: '>=' })
		options.push({ label: 'less than', value: '<' })
		options.push({ label: 'less than or equals', value: '<=' })
		options.push({ label: 'between', value: 'between' })
		options.push({ label: 'within', value: 'within' })
		options.push({ label: 'is set', value: 'is_set' })
		options.push({ label: 'is not set', value: 'is_not_set' })
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
