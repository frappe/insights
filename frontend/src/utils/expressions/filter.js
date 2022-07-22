export function toLogicalExpression(binaryExpression) {
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
	if (isLogicalOperator(binaryExpression.operator)) {
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
	}
	return binaryExpression
}

export function mergeConditions(ast) {
	// merges conditions under same logical operator
	// eg.
	// {                                                     {
	//  "type": "LogExp",                                      "type": "LogExp",
	//  "operator": "&&",                                      "operator": "&&",
	//  "conditions": [                                        "conditions": [
	//    {                                                      { "type": "Number", "value": 1 },
	//      "type": "LogExp",                                    { "type": "Number", "value": 2 },
	//      "operator": "&&",                                    {
	//      "conditions": [                                        "type": "LogExp",
	//        { "type": "Number", "value": 1 },    MERGES          "operator": "||",
	//        { "type": "Number", "value": 2 }      INTO           "conditions": [
	//      ]                                                         { "type": "Number", "value": 3 },
	//    },                                                          { "type": "Number", "value": 4 }
	//    {                                                        ]
	//      "type": "LogExp",                                    }
	//      "operator": "||",                                  ]
	//      "conditions": [                                  }
	//        { "type": "Number", "value": 3 },
	//        { "type": "Number", "value": 4 }
	//      ]
	//    }
	//  ]
	// }

	if (ast.type == 'LogicalExpression') {
		if (!ast.conditions.some((c) => c.operator == ast.operator)) {
			return ast
		}

		const replaceConditionMap = {}
		ast.conditions.forEach((condition, idx) => {
			if (condition.type == 'LogicalExpression' && condition.operator == ast.operator) {
				replaceConditionMap[idx] = condition.conditions
			}
		})
		Object.keys(replaceConditionMap).forEach((idx) => {
			ast.conditions.splice(idx, 1, ...replaceConditionMap[idx])
		})
		return mergeConditions(ast)
	}
	return ast
}
