import { safeJSONParse } from '@/utils'
import { reactive, ref, watch, computed } from 'vue'
import { FIELDTYPES } from '@/utils/query'
import { getColumn } from '@/utils/query/columns'
import { convertIntoQueryFilters } from '@/utils/expressions/filter'

export function useQueryFilters(query) {
	const data = computed(() => {
		return safeJSONParse(query.doc.filters, {})
	})

	const addNextFilterAt = reactive({
		level: 1,
		position: 1,
	})
	const editFilterAt = reactive({
		level: 1,
		position: 1,
		idx: -1,
	})

	const add = (filter) => {
		const expression = getLogicalExpressionAt({
			...addNextFilterAt,
			filters: data.value,
		})
		expression.conditions.push(filter)
		updateFilters()
	}
	const edit = (filter) => {
		const expression = getLogicalExpressionAt({
			...editFilterAt,
			filters: data.value,
		})
		expression.conditions[editFilterAt.idx] = filter
		updateFilters()
	}
	const remove = (level, position, idx) => {
		if (level == 1 && typeof idx == 'number') {
			// remove the filter from root level
			data.value.conditions.splice(idx, 1)
		}

		if (level > 1 && position && typeof idx == 'number') {
			// remove the filter at `idx` from the filter group at `level` & `position`
			const expression = getLogicalExpressionAt({ filters: data.value, level, position })
			expression.conditions.splice(idx, 1)
		}

		updateFilters()
	}
	const toggleOperator = (level, position) => {
		const expression = getLogicalExpressionAt({ filters: data.value, level, position })
		expression.operator = expression.operator == '&&' ? '||' : '&&'
		updateFilters()
	}

	const updateFilters = () => {
		let filters = convertIntoQueryFilters(data.value)
		query.updateFilters.submit({ filters })
	}

	return {
		data,
		addNextFilterAt,
		editFilterAt,
		add,
		edit,
		remove,
		toggleOperator,
		convertIntoExpression,
		convertIntoSimpleFilter,
	}
}

function getLogicalExpressionAt({ filters, level, position, parentIdx }) {
	if (level == 1 && position == 1) {
		return filters
	}

	let expression = null
	for (let i = 0; i < filters.conditions.length; i++) {
		let exp = filters.conditions[i]
		if (exp.type !== 'LogicalExpression') continue

		if (exp.level == level && (exp.position == position || i == parentIdx)) {
			expression = exp
			break
		}

		if (exp.conditions?.length > 0) {
			let _exp = getLogicalExpressionAt({ filters: exp, level, position })
			if (_exp) {
				expression = _exp
				break
			}
		}
	}
	return expression
}

const BINARY_OPERATORS = {
	'=': 'equals',
	'!=': 'not equals',
	'>': 'greater than',
	'>=': 'greater than equal to',
	'<': 'less than',
	'<=': 'less than equal to',
}
const CALL_FUNCTIONS = {
	is: 'is',
	in: 'in',
	not_in: 'not in',
	between: 'between',
	timespan: 'within',
	starts_with: 'starts with',
	ends_with: 'ends with',
	contains: 'contains',
	not_contains: 'not contains',
}

function isBinaryOperator(operator) {
	return Boolean(BINARY_OPERATORS[operator])
}
function isCallFunction(operator) {
	return Boolean(CALL_FUNCTIONS[operator])
}

function convertIntoBinaryExpression(simpleFilter) {
	const { column, operator, value } = simpleFilter
	return {
		type: 'BinaryExpression',
		operator: operator.value,
		left: {
			type: 'Column',
			value: {
				column: column.column,
				table: column.table,
			},
		},
		right: {
			type: FIELDTYPES.NUMBER.includes(column.type) ? 'Number' : 'String',
			value: value.value,
		},
	}
}

function convertIntoCallExpression(simpleFilter) {
	const { column, operator, value } = simpleFilter

	const operatorFunction =
		operator.value == 'is' ? (value.value == 'set' ? 'isnotnull' : 'isnull') : operator.value

	function makeArgs() {
		if (operator.value == 'is') return []
		if (operator.value == 'between') {
			const values = value.value.split(',')
			return values.map((v) => ({
				type: FIELDTYPES.NUMBER.includes(column.type) ? 'Number' : 'String',
				value: v,
			}))
		}
		if (['in', 'not_in'].includes(operator.value)) {
			return value.value.map((v) => ({ type: 'String', value: v }))
		}
		return [{ type: 'String', value: value.value }]
	}

	return {
		type: 'CallExpression',
		function: operatorFunction,
		arguments: [
			{
				type: 'Column',
				value: {
					column: column.column,
					table: column.table,
				},
			},
			...makeArgs(),
		],
	}
}

export function convertIntoExpression(simpleFilter) {
	const operator = simpleFilter.operator.value
	if (isBinaryOperator(operator)) {
		return convertIntoBinaryExpression(simpleFilter)
	}
	if (isCallFunction(operator)) {
		return convertIntoCallExpression(simpleFilter)
	}
}

export function convertIntoSimpleFilter(expression) {
	if (isBinaryOperator(expression.operator)) {
		const column = getColumn(expression.left.value)
		const operator = {
			label: BINARY_OPERATORS[expression.operator],
			value: expression.operator,
		}
		const value = {
			label: expression.right.value,
			value: expression.right.value,
		}
		return { column, operator, value }
	}

	if (isCallFunction(expression.function)) {
		const column = getColumn(expression.arguments[0].value)
		const operatorFunction = ['isnull', 'isnotnull'].includes(expression.function)
			? 'is'
			: expression.function
		const operator = {
			label: CALL_FUNCTIONS[operatorFunction],
			value: operatorFunction,
		}

		function makeValue() {
			if (expression.function == 'isnull') return 'Not Set'
			if (expression.function == 'isnotnull') return 'Set'
			if (expression.function == 'between') {
				return expression.arguments[1].value + ',' + expression.arguments[2].value
			}
			if (['in', 'not_in'].includes(expression.function)) {
				return expression.arguments
					.slice(1)
					.map((a) => ({ label: a.value, value: a.value }))
			}
			return expression.arguments[1].value
		}

		const value = makeValue()
		return { column, operator, value: { label: value, value } }
	}
}
