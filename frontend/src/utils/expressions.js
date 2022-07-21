function isNumber(char) {
	return /^[0-9]$/.test(char)
}

function isOperator(char) {
	return (
		char === '+' ||
		char === '-' ||
		char === '*' ||
		char === '/' ||
		char === '>' ||
		char === '<' ||
		char === '=' ||
		char === '!=' ||
		char === '>=' ||
		char === '<='
	)
}

function isParenthesis(char) {
	return /^[()]$/.test(char)
}

function isWhiteSpace(char) {
	return /^\s$/.test(char)
}

const TOKEN_TYPES = {
	EOF: 'EOF',
	NUMBER: 'NUMBER',
	PARENTHESIS: 'PARENTHESIS',
	OPERATOR_ADD: 'OPERATOR_ADD',
	OPERATOR_SUB: 'OPERATOR_SUB',
	OPERATOR_MUL: 'OPERATOR_MUL',
	OPERATOR_DIV: 'OPERATOR_DIV',
	OPERATOR_GT: 'OPERATOR_GT',
	OPERATOR_LT: 'OPERATOR_LT',
	OPERATOR_EQ: 'OPERATOR_EQ',
	OPERATOR_NEQ: 'OPERATOR_NEQ',
	OPERATOR_GTE: 'OPERATOR_GTE',
	OPERATOR_LTE: 'OPERATOR_LTE',
	OPEN_SQUARE_BRACKET: 'OPEN_SQUARE_BRACKET',
	CLOSE_SQUARE_BRACKET: 'CLOSE_SQUARE_BRACKET',
	COLUMN: 'COLUMN',
}

function getOperatorTokenType(operator) {
	switch (operator) {
		case '+':
			return TOKEN_TYPES.OPERATOR_ADD
		case '-':
			return TOKEN_TYPES.OPERATOR_SUB
		case '*':
			return TOKEN_TYPES.OPERATOR_MUL
		case '/':
			return TOKEN_TYPES.OPERATOR_DIV
		case '>':
			return TOKEN_TYPES.OPERATOR_GT
		case '<':
			return TOKEN_TYPES.OPERATOR_LT
		case '=':
			return TOKEN_TYPES.OPERATOR_EQ
		case '!=':
			return TOKEN_TYPES.OPERATOR_NEQ
		case '>=':
			return TOKEN_TYPES.OPERATOR_GTE
		case '<=':
			return TOKEN_TYPES.OPERATOR_LTE
		default:
			throw new Error(`Unknown operator: ${operator}`)
	}
}

function tokenize(expression) {
	let cursor = 0
	let tokens = []
	let char = expression[cursor]

	function advance() {
		char = expression[++cursor]
	}

	function getNumberToken() {
		let number = ''
		while (isNumber(char) || (char == '.' && isNumber(expression[cursor + 1]))) {
			number += char
			advance()
		}
		return {
			type: TOKEN_TYPES.NUMBER,
			value: number,
		}
	}

	function processColumnToken() {
		tokens.push({
			type: TOKEN_TYPES.OPEN_SQUARE_BRACKET,
			position: cursor,
		})
		advance()

		let columnStr = ''
		while (char != ']' && cursor < expression.length) {
			columnStr += char
			advance()
		}
		if (columnStr.length) {
			const start = cursor - columnStr.length
			const [table, column] = columnStr.split('.')
			tokens.push({
				type: TOKEN_TYPES.COLUMN,
				start: start,
				end: cursor,
				value: {
					table: column ? table : null,
					column: column ? column : table,
				},
			})
		}

		if (char === ']') {
			tokens.push({
				type: TOKEN_TYPES.CLOSE_SQUARE_BRACKET,
				position: cursor,
			})
			advance()
		}
	}

	while (cursor < expression.length) {
		if (isWhiteSpace(char)) {
			advance()
			continue
		}

		if (isOperator(char)) {
			tokens.push({
				type: getOperatorTokenType(char),
				value: char,
			})
			advance()
			continue
		}

		if (isParenthesis(char)) {
			tokens.push({
				type: TOKEN_TYPES.PARENTHESIS,
				value: char,
			})
			advance()
			continue
		}

		if (isNumber(char)) {
			const number = getNumberToken()
			tokens.push(number)
			continue
		}

		if (isOpenSquareBracket(char)) {
			processColumnToken()
			continue
		}

		throw new Error(`Unexpected character: ${char} while parsing expression: ${expression}`)
	}

	tokens.push({
		type: TOKEN_TYPES.EOF,
	})

	return tokens
}

function isOpenSquareBracket(char) {
	return char === '['
}

const MAX_PRECEDENCE = 4
function getPrecedence(tokenType) {
	switch (tokenType) {
		case TOKEN_TYPES.NUMBER:
		case TOKEN_TYPES.PARENTHESIS:
		case TOKEN_TYPES.OPEN_SQUARE_BRACKET:
		case TOKEN_TYPES.CLOSE_SQUARE_BRACKET:
		case TOKEN_TYPES.COLUMN:
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
			case TOKEN_TYPES.PARENTHESIS:
				return parseParenthesis()
			case TOKEN_TYPES.OPEN_SQUARE_BRACKET:
				return parseColumn()
			case TOKEN_TYPES.EOF:
				return { type: 'EOF' }
			default:
				throw new Error(
					`Failed to Parse Expression ${expression}: Unexpected token: ${currentToken.type}`
				)
		}
	}

	function parseNumber() {
		const value = currentToken.value
		currentToken = tokens[++cursor]
		return { type: 'NumberLiteral', value: parseFloat(value) }
	}

	function parseParenthesis() {
		currentToken = tokens[++cursor]
		const expr = parseFor(1)
		if (currentToken.type != TOKEN_TYPES.PARENTHESIS) {
			throw new Error(
				`Failed to Parse Expression ${expression}: Expected closing parenthesis, got: ${currentToken.type}`
			)
		}
		currentToken = tokens[++cursor]
		return expr
	}

	function parseColumn() {
		currentToken = tokens[++cursor]
		if (currentToken.type !== TOKEN_TYPES.COLUMN) {
			throw new Error(
				`Failed to Parse Expression ${expression}: Expected column reference, got: ${currentToken.type}`
			)
		}
		const column = currentToken.value
		currentToken = tokens[++cursor]
		if (currentToken.type !== TOKEN_TYPES.CLOSE_SQUARE_BRACKET) {
			throw new Error(
				`Failed to Parse Expression ${expression}: Expected closing square bracket, got: ${currentToken.type}`
			)
		}
		currentToken = tokens[++cursor]
		return { type: 'ColumnLiteral', value: column }
	}

	return { parsed: parseFor(1), tokens }
}
