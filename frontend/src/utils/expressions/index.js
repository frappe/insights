import tokenize from '@/utils/expressions/tokenize'
import { TOKEN_TYPES } from '@/utils/expressions/tokenize'

const MAX_PRECEDENCE = 4

function getPrecedence(tokenType) {
	switch (tokenType) {
		case TOKEN_TYPES.NUMBER:
		case TOKEN_TYPES.STRING:
		case TOKEN_TYPES.COLUMN:
		case TOKEN_TYPES.FUNCTION:
		case TOKEN_TYPES.OPEN_PARENTHESIS:
		case TOKEN_TYPES.CLOSE_PARENTHESIS:
		case TOKEN_TYPES.OPEN_SQUARE_BRACKET:
		case TOKEN_TYPES.CLOSE_SQUARE_BRACKET:
			return MAX_PRECEDENCE
		case TOKEN_TYPES.OPERATOR_MUL:
		case TOKEN_TYPES.OPERATOR_DIV:
			return 3
		case TOKEN_TYPES.OPERATOR_ADD:
		case TOKEN_TYPES.OPERATOR_SUB:
			return 2
		case TOKEN_TYPES.OPERATOR_GT:
		case TOKEN_TYPES.OPERATOR_LT:
		case TOKEN_TYPES.OPERATOR_EQ:
		case TOKEN_TYPES.OPERATOR_NEQ:
		case TOKEN_TYPES.OPERATOR_GTE:
		case TOKEN_TYPES.OPERATOR_LTE:
			return 1
		default:
			return 100
	}
}

export function parse(expression) {
	const tokens = tokenize(expression)

	let cursor = 0
	let currentToken = tokens[cursor]
	let errorMessage = null

	function parseFor(precedence) {
		if (precedence < MAX_PRECEDENCE) {
			let left = parseFor(precedence + 1)
			while (getPrecedence(currentToken.type) == precedence) {
				const operator = currentToken.value
				currentToken = tokens[++cursor]
				const right = parseFor(precedence + 1)
				left = { type: 'BinaryExpression', operator, left, right }
			}
			return left
		}

		// precedence == MAX_PRECEDENCE
		switch (currentToken.type) {
			case TOKEN_TYPES.NUMBER:
				return parseNumber()
			case TOKEN_TYPES.STRING:
				return parseString()
			case TOKEN_TYPES.OPEN_PARENTHESIS:
				return parseParenthesis()
			case TOKEN_TYPES.OPEN_SQUARE_BRACKET:
				return parseColumn()
			case TOKEN_TYPES.FUNCTION:
				return parseFunction()
			case TOKEN_TYPES.EOF:
				return { type: 'EOF' }
			default:
				errorMessage = `Unexpected token: ${currentToken.value}`
				throw new Error(
					`Failed to Parse Expression ${expression}: Unexpected token: ${currentToken.type}`
				)
		}
	}

	function parseNumber() {
		const value = currentToken.value
		currentToken = tokens[++cursor]
		return { type: 'Number', value: parseFloat(value) }
	}

	function parseString() {
		const value = currentToken.value
		currentToken = tokens[++cursor]
		return { type: 'String', value }
	}

	function parseParenthesis() {
		currentToken = tokens[++cursor]
		if (!checkForClosingParenthesis()) {
			errorMessage = `Missing closing parenthesis for opening parenthesis`
			throw new Error(`Failed to Parse Expression ${expression}: Missing closing parenthesis`)
		}
		const expr = parseFor(1)
		currentToken = tokens[++cursor]
		return expr
	}

	function parseColumn() {
		currentToken = tokens[++cursor]
		if (currentToken.type !== TOKEN_TYPES.COLUMN) {
			errorMessage = `Missing column name`
			throw new Error(
				`Failed to Parse Expression ${expression}: Expected column reference, got: ${currentToken.type}`
			)
		}

		const column = currentToken.value
		if (!column.table || !column.column) {
			errorMessage = `Invalid column reference`
			throw new Error(
				`Failed to Parse Expression ${expression}: Invalid column reference: ${column}`
			)
		}

		currentToken = tokens[++cursor]
		if (currentToken.type !== TOKEN_TYPES.CLOSE_SQUARE_BRACKET) {
			errorMessage = `Missing closing square bracket`
			throw new Error(
				`Failed to Parse Expression ${expression}: Expected closing square bracket, got: ${currentToken.type}`
			)
		}
		currentToken = tokens[++cursor]
		return { type: 'Column', value: column }
	}

	function parseFunction() {
		const name = currentToken.value
		currentToken = tokens[++cursor]
		if (currentToken.type !== TOKEN_TYPES.OPEN_PARENTHESIS) {
			errorMessage = `Expected opening parenthesis after function ${name}`
			throw new Error(
				`Failed to Parse Expression ${expression}: Expected opening parenthesis, got: ${currentToken.type}`
			)
		}
		currentToken = tokens[++cursor]

		if (!checkForClosingParenthesis()) {
			errorMessage = `Missing closing parenthesis for function ${name}`
			throw new Error(
				`Failed to Parse Expression ${expression}: Missing closing parenthesis for function ${name}`
			)
		}

		const args = []
		while (currentToken.type !== TOKEN_TYPES.CLOSE_PARENTHESIS) {
			args.push(parseFor(1))
			if (currentToken.type === TOKEN_TYPES.ARGUMENT_SEPARATOR) {
				currentToken = tokens[++cursor]
			}
		}
		currentToken = tokens[++cursor]
		return { type: 'FunctionCall', function: name, arguments: args }
	}

	function checkForClosingParenthesis() {
		// find the closing parenthesis after the opening one if not found, throw error
		let closingParenthesisIndex = -1
		for (let i = cursor; i < tokens.length; i++) {
			if (tokens[i].type === TOKEN_TYPES.CLOSE_PARENTHESIS) {
				closingParenthesisIndex = i
				break
			}
		}
		if (closingParenthesisIndex !== -1) {
			return true
		}
	}

	let ast = null
	try {
		ast = parseFor(1)
	} catch (error) {
		console.groupCollapsed('Failed to Parse Expression')
		console.error(error)
		console.groupEnd()
	}

	return {
		ast,
		errorMessage,
		tokens: tokens,
	}
}
