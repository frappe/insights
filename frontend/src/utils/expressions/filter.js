function toLogicalExpression(binaryExpression) {
	// converts a binary expression with logical operators to a logical expression
	// logical expression schema
	// {
	// 	type: "LogicalExpression",
	// 	operator: "&&" | "||",
	// 	conditions: [ left, right ]
	// }
	function isLogicalOperator(operator) {
		return operator === '&&' || operator === '||'
	}
	if (!isLogicalOperator(binaryExpression.operator)) {
		return binaryExpression
	}

	function shouldConvert(expression) {
		return (
			expression.type == 'BinaryExpression' &&
			isLogicalOperator(expression.operator) &&
			binaryExpression.left &&
			binaryExpression.right
		)
	}
	if (shouldConvert(binaryExpression)) {
		const { left, right } = binaryExpression

		binaryExpression.type = 'LogicalExpression'
		binaryExpression.conditions = binaryExpression.conditions || []
		delete binaryExpression.left
		delete binaryExpression.right

		binaryExpression.conditions.push(
			isLogicalOperator(left.operator) ? toLogicalExpression(left) : left
		)

		binaryExpression.conditions.push(
			isLogicalOperator(right.operator) ? toLogicalExpression(right) : right
		)

		return binaryExpression
	}

	if (
		binaryExpression.type == 'LogicalExpression' &&
		isLogicalOperator(binaryExpression.operator) &&
		binaryExpression.conditions.length > 0
	) {
		binaryExpression.conditions.forEach((condition, idx) => {
			binaryExpression.conditions[idx] = toLogicalExpression(condition)
		})
	}
	return binaryExpression
}

function mergeConditions(ast) {
	// merges sub conditions with same logical operator into parent condition
	// eg.
	//              A > B                   A > B
	//      | AND - A > C                   A > C
	// AND -                         AND -  B > C
	//     | AND - B > C                    B > D
	//             B > D

	if (ast.type !== 'LogicalExpression' || ast.conditions.length == 0) {
		return ast
	}

	function shouldMerge(condition) {
		return condition.conditions.some((c) => c.operator == condition.operator)
	}

	if (shouldMerge(ast)) {
		const replaceConditionMap = {}
		ast.conditions.forEach((condition, idx) => {
			if (condition.type == 'LogicalExpression' && condition.operator == ast.operator) {
				replaceConditionMap[idx] = condition.conditions
			}
		})
		Object.keys(replaceConditionMap).forEach((idx) => {
			ast.conditions.splice(idx, 1, ...replaceConditionMap[idx])
		})
	}
	ast.conditions.forEach((c) => mergeConditions(c))
	return ast
}

function setLevelAndPosition(filters) {
	function _setLevelAndPosition(tree) {
		tree.conditions?.forEach((condition, idx) => {
			if (condition.type == 'LogicalExpression') {
				condition.level = tree.level + 1
				condition.position = idx + 1
				if (condition.conditions.length > 0) {
					_setLevelAndPosition(condition)
				}
			}
		})
		return tree
	}
	filters.level = 1
	filters.position = 1
	return _setLevelAndPosition(filters)
}

export function convertIntoQueryFilters(ast) {
	if (ast.type !== 'LogicalExpression') {
		return ast
	}

	let filters = ast
	filters = toLogicalExpression(filters)
	filters = mergeConditions(filters)
	filters = setLevelAndPosition(filters)
	return filters
}
