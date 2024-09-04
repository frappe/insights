import { FIELDTYPES } from '../../helpers/constants'
import { ColumnDataType, FilterExpression, FilterRule } from '../../types/query.types'

export function getValueSelectorType(filter: FilterRule, columnType: ColumnDataType) {
	if (!filter.column.column_name || !filter.operator) return 'text' // default to text
	if (['is_set', 'is_not_set'].includes(filter.operator)) return

	if (FIELDTYPES.TEXT.includes(columnType)) {
		return ['in', 'not_in'].includes(filter.operator) ? 'select' : 'text'
	}
	if (FIELDTYPES.NUMBER.includes(columnType)) return 'number'
	if (FIELDTYPES.DATE.includes(columnType)) {
		return filter.operator === 'between' ? 'date_range' : 'date'
	}
	return 'text'
}

export function isFilterExpressionValid(filter: FilterExpression) {
	return filter.expression.expression.trim().length > 0
}

export function isFilterValid(filter: FilterRule, columnType: ColumnDataType) {
	if (!filter.column.column_name || !filter.operator) {
		return false
	}
	if (!filter.column.column_name || !filter.operator) {
		return false
	}

	const valueSelectorType = getValueSelectorType(filter, columnType)

	// if selector type is none, no need to validate
	if (!valueSelectorType) {
		return true
	}

	if (!filter.value && filter.value !== 0) {
		return false
	}

	// for number, validate if it's a number
	if (FIELDTYPES.NUMBER.includes(columnType)) {
		return !isNaN(filter.value as any)
	}

	// for text,
	// if it's a select, validate if it's an array of strings
	// if it's a text, validate if it's a string
	if (FIELDTYPES.TEXT.includes(columnType)) {
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
	if (FIELDTYPES.DATE.includes(columnType)) {
		if (valueSelectorType === 'date') {
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
