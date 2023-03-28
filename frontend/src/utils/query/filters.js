import { FIELDTYPES, safeJSONParse } from '@/utils'
import { convertIntoQueryFilters } from '@/utils/expressions/filter'
import { getColumn } from '@/utils/query/columns'
import { computed, reactive } from 'vue'

const DEFAULT_FILTERS = {
	type: 'LogicalExpression',
	level: 1,
	position: 1,
	operator: '&&',
	conditions: [],
}

export function useQueryFilters(query) {
	const data = computed(() => safeJSONParse(query.doc.filters, DEFAULT_FILTERS))

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
		Object.assign(editFilterAt, {
			level: 1,
			position: 1,
			idx: -1,
		})
		updateFilters()
	}
	const remove = (level, position, idx) => {
		if (level == 1 && typeof idx == 'number') {
			// remove the filter from root level
			data.value.conditions.splice(idx, 1)
		}

		if (level > 1 && position && typeof idx == 'number') {
			// remove the filter at `idx` from the filter group at `level` & `position`
			const expression = getLogicalExpressionAt({
				filters: data.value,
				level,
				position,
			})
			expression.conditions.splice(idx, 1)
		}

		updateFilters()
	}
	const toggleOperator = (level, position) => {
		const expression = getLogicalExpressionAt({
			filters: data.value,
			level,
			position,
		})
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
		isSimpleFilter,
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

// utility functions to convert a simple filter into expression and vice versa
export const BINARY_OPERATORS = {
	'=': 'equals',
	'!=': 'not equals',
	'>': 'greater than',
	'>=': 'greater than equal to',
	'<': 'less than',
	'<=': 'less than equal to',
}
export const FILTER_FUNCTIONS = {
	is: 'is',
	in: 'one of',
	not_in: 'not one of',
	between: 'between',
	timespan: 'within',
	starts_with: 'starts with',
	ends_with: 'ends with',
	contains: 'contains',
	not_contains: 'not contains',
}

function getOperatorFromCallFunction(functionName) {
	if (FILTER_FUNCTIONS[functionName]) {
		return functionName
	}
	if (functionName.indexOf('set') > -1) {
		return 'is'
	}
	// is not a simple filter call function
	return null
}
function isBinaryOperator(operator) {
	return Boolean(BINARY_OPERATORS[operator])
}
function isCallFunction(functionName) {
	return Boolean(FILTER_FUNCTIONS[getOperatorFromCallFunction(functionName)])
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
		operator.value == 'is' ? (value.value == 'set' ? 'is_set' : 'is_not_set') : operator.value

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

function areLiterals(args) {
	return args.every((arg) => arg.type == 'String' || arg.type == 'Number')
}

function makeValueFromCallFunction(expression) {
	if (!areLiterals(expression.arguments.slice(1))) return []
	if (expression.function == 'is_set') return ['Set', 'Set']
	if (expression.function == 'is_not_set') return ['Not Set', 'Not Set']
	if (expression.function == 'between') {
		const value = expression.arguments[1].value + ', ' + expression.arguments[2].value
		return [value, value]
	}
	if (['in', 'not_in'].includes(expression.function)) {
		const values = expression.arguments.slice(1).map((a) => a.value)
		const label = values.length > 1 ? values.length + ' values' : values[0]
		return [label, values]
	}
	const value = expression.arguments[1].value
	return [value, value]
}

export function isSimpleFilter(expression) {
	// an expression is a simple filter if it can be converted into a simple filter
	// with proper column, operator and value
	const simpleFilter = convertIntoSimpleFilter(expression)
	if (!simpleFilter) return false
	const { column, operator, value } = simpleFilter
	if (!column || !operator || !value) return false
	if (!column.value || !operator.value || !value.value) return false
	return true
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
		const operator = getOperatorFromCallFunction(expression.function)
		const column = getColumn(expression.arguments[0].value)
		const [label, value] = makeValueFromCallFunction(expression)
		return {
			column: column,
			operator: {
				label: FILTER_FUNCTIONS[operator],
				value: operator,
			},
			value: {
				label: label || value,
				value: value,
			},
		}
	}
}
