export const TOKEN_TYPES = {
	EOF: 'EOF',
	NUMBER: 'NUMBER',
	OPEN_PARENTHESIS: 'OPEN_PARENTHESIS',
	CLOSE_PARENTHESIS: 'CLOSE_PARENTHESIS',
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
	BACKTICK: 'BACKTICK',
	COLUMN: 'COLUMN',
	FUNCTION: 'FUNCTION',
	ARGUMENT_SEPARATOR: 'ARGUMENT_SEPARATOR',
	FUNCTION_ARGUMENTS: 'FUNCTION_ARGUMENTS',
	STRING: 'STRING',
	LOGICAL_AND: 'LOGICAL_AND',
	LOGICAL_OR: 'LOGICAL_OR',
}

const FUNCTION_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$'

function isParenthesis(char) {
	return /^[()]$/.test(char)
}

function isWhiteSpace(char) {
	return /^\s$/.test(char)
}

function isNumber(char) {
	return /^[0-9]$/.test(char)
}

function isBackTick(char) {
	return char === '`'
}

function isArgumentSeparator(char) {
	return char === ','
}

function isQuote(char) {
	return char === '"' || char === "'"
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
		char === '!'
	)
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
			console.warn(`Unknown operator: ${operator}`)
	}
}

function isLogicalOperator(char) {
	return char === '&' || char === '|'
}

export default function tokenize(expression, offset = 0) {
	// remove tabs, form-feed, carriage returns, and newlines
	expression = expression?.replace(/\t\f\r\n/g, '')
	if (!expression) return []

	let cursor = 0
	let tokens = []
	let char = expression[cursor]
	let nextChar = expression[cursor + 1]

	function advance() {
		char = expression[++cursor]
		nextChar = expression[cursor + 1]
	}

	function processOperatorToken() {
		let operator = ''
		while (isOperator(char)) {
			operator += char
			advance()
		}
		tokens.push({
			type: getOperatorTokenType(operator),
			value: operator,
		})
	}

	function processNumberToken() {
		let number = ''
		while (isNumber(char) || (char == '.' && isNumber(expression[cursor + 1]))) {
			number += char
			advance()
		}
		tokens.push({
			type: TOKEN_TYPES.NUMBER,
			value: number,
		})
	}

	function processColumnToken() {
		tokens.push({
			type: TOKEN_TYPES.BACKTICK,
		})
		advance()

		let columnStr = ''
		while (char != '`' && cursor < expression.length) {
			columnStr += char
			advance()
		}
		if (columnStr.length) {
			const start = offset + cursor - columnStr.length
			const [table, column] = columnStr.split('.')
			tokens.push({
				type: TOKEN_TYPES.COLUMN,
				start: start,
				end: offset + cursor,
				value: {
					table: column ? table : null,
					column: column ? column : table,
				},
			})
		}

		if (char === '`') {
			tokens.push({
				type: TOKEN_TYPES.BACKTICK,
			})
			advance()
		}
	}

	function processFunctionToken() {
		let fn = ''
		while (FUNCTION_CHARS.includes(char) && cursor < expression.length) {
			fn += char
			advance()
		}
		if (!fn) return
		const fnToken = {
			type: TOKEN_TYPES.FUNCTION,
			start: offset + cursor - fn.length,
			end: offset + cursor,
			value: fn,
		}

		let openParenToken = null
		if (char === '(') {
			openParenToken = {
				type: TOKEN_TYPES.OPEN_PARENTHESIS,
			}
			advance()
		}

		let argsStart = cursor
		let closeParenthesis = findMatchingParenthesis(expression, cursor - 1)
		let argsEnd = closeParenthesis !== -1 ? closeParenthesis : expression.length
		let argsStr = expression.substring(argsStart, argsEnd)
		if (!argsStr) {
			fnToken.end = offset + cursor
			tokens.push(fnToken)
			openParenToken && tokens.push(openParenToken)
			return
		}
		let fnArgs = tokenize(argsStr, offset + argsStart).filter(
			(token) => token.type !== TOKEN_TYPES.EOF
		)

		cursor = argsEnd - 1
		advance()
		let closeParenToken = null
		if (char === ')') {
			closeParenToken = {
				type: TOKEN_TYPES.CLOSE_PARENTHESIS,
			}
			advance()
		}

		fnToken.end = offset + cursor
		tokens.push(fnToken)
		openParenToken && tokens.push(openParenToken)
		tokens = tokens.concat(fnArgs)
		closeParenToken && tokens.push(closeParenToken)
	}

	function processStringToken() {
		let quote = char
		advance()
		let string = ''
		while (char != quote && cursor < expression.length) {
			string += char
			advance()
		}
		if (char == quote) {
			tokens.push({
				type: TOKEN_TYPES.STRING,
				value: string,
			})
			advance()
		}
	}

	function processLogicalOperatorToken() {
		tokens.push({
			type: char == '&' ? TOKEN_TYPES.LOGICAL_AND : TOKEN_TYPES.LOGICAL_OR,
			value: char + nextChar,
		})
		advance()
		advance()
	}

	while (cursor < expression.length) {
		if (isWhiteSpace(char)) {
			advance()
			continue
		}

		if (isOperator(char)) {
			processOperatorToken()
			continue
		}

		if (isParenthesis(char)) {
			tokens.push({
				type: char == '(' ? TOKEN_TYPES.OPEN_PARENTHESIS : TOKEN_TYPES.CLOSE_PARENTHESIS,
			})
			advance()
			continue
		}

		if (isArgumentSeparator(char)) {
			tokens.push({
				type: TOKEN_TYPES.ARGUMENT_SEPARATOR,
				value: char,
			})
			advance()
			continue
		}

		if (isNumber(char)) {
			processNumberToken()
			continue
		}

		if (isBackTick(char)) {
			processColumnToken()
			continue
		}

		if (isQuote(char)) {
			processStringToken()
			continue
		}

		if (isLogicalOperator(char) && isLogicalOperator(char) == isLogicalOperator(nextChar)) {
			processLogicalOperatorToken()
			continue
		}

		if (FUNCTION_CHARS.includes(char)) {
			processFunctionToken()
			continue
		}

		console.warn(`Unexpected character: ${char} while parsing expression: ${expression}`)
		break
	}

	tokens.push({
		type: TOKEN_TYPES.EOF,
	})

	return tokens
}

function findMatchingParenthesis(str, start) {
	if (str[start] !== '(') return -1
	let open = 0
	for (let i = start; i < str.length; i++) {
		if (str[i] == '(') open++
		if (str[i] == ')') open--
		if (open == 0) return i
	}
	return -1
}
