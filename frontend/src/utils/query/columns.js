import { reactive, computed, watch } from 'vue'
import { isEqual } from '@/utils'
import { FIELDTYPES } from '@/utils/query'

const cache = reactive({
	columns: {},
})

export function useQueryColumns(query) {
	const data = computed(() =>
		query.doc.columns.map((column) => {
			return {
				...column,
				format_option: column.format_option ? safeJSONParse(column.format_option) : null,
				aggregation_condition: column.aggregation_condition
					? safeJSONParse(column.aggregation_condition)
					: null,
			}
		})
	)

	// if tables changes then update columns options
	watch(
		() => query.doc?.tables?.map((row) => row.table),
		(newVal, oldVal) => {
			if (!isEqual(newVal, oldVal)) {
				query.fetchColumns.submit()
			}
		},
		{ immediate: true }
	)
	const options = computed(() =>
		query.fetchColumns.data?.message.map((c) => {
			return {
				...c,
				value: c.column, // calc value key for autocomplete options
				description: c.table_label,
			}
		})
	)
	watch(options, updateColumnOptionsCache)

	return { data, options, getOperatorOptions }
}

function updateColumnOptionsCache(columns) {
	cache.columns = columns.reduce((acc, column) => {
		const key = `${column.table}_${column.column}`
		if (!acc[key]) {
			acc[key] = column
		}
		return acc
	}, cache.columns)
}

export function getColumn(column) {
	const cachedColumn = cache.columns[`${column.table}_${column.column}`]
	if (cachedColumn) {
		return cachedColumn
	}
}

export function getOperatorOptions(columnType) {
	let options = [
		{ label: 'equals', value: '=' },
		{ label: 'not equals', value: '!=' },
		{ label: 'is', value: 'is' },
	]

	if (!columnType) {
		return options
	}

	if (FIELDTYPES.TEXT.includes(columnType)) {
		options = options.concat([
			{ label: 'contains', value: 'contains' },
			{ label: 'not contains', value: 'not_contains' },
			{ label: 'starts with', value: 'starts_with' },
			{ label: 'ends with', value: 'ends_with' },
			{ label: 'in', value: 'in' },
			{ label: 'not in', value: 'not_in' },
		])
	}
	if (FIELDTYPES.NUMBER.includes(columnType)) {
		options = options.concat([
			{ label: 'in', value: 'in' },
			{ label: 'not in', value: 'not_in' },
			{ label: 'greater than', value: '>' },
			{ label: 'smaller than', value: '<' },
			{ label: 'greater than equal to', value: '>=' },
			{ label: 'smaller than equal to', value: '<=' },
			{ label: 'between', value: 'between' },
		])
	}
	if (FIELDTYPES.DATE.includes(columnType)) {
		options = options.concat([
			{ label: 'greater than', value: '>' },
			{ label: 'smaller than', value: '<' },
			{ label: 'greater than equal to', value: '>=' },
			{ label: 'smaller than equal to', value: '<=' },
			{ label: 'between', value: 'between' },
			{ label: 'within', value: 'timespan' },
		])
	}
	return options
}
