import { describe, expect, it } from 'vitest'
import { getErrorMessage } from './index'

// What frappe-ui's `frappeRequest` rejects with. `messages` is the sentence the
// server refused with, from `_server_messages`, which every user is sent; `exc`
// is the traceback, sent to a System User only.
function refusal(fields: { messages?: string[]; exc?: string }) {
	return Object.assign(new Error('/api/method/run_doc_method ValidationError'), fields)
}

const SENTENCE =
	'Fill in the value of the variable <strong>api_key</strong> on this query to run it.'

describe('getErrorMessage', () => {
	// @feature permissions.error-is-text
	it('reads the sentence to a user sent no traceback', () => {
		// a plain Insights user: the Insights User role has no desk access
		expect(getErrorMessage(refusal({ messages: [SENTENCE] }))).toBe(
			'Fill in the value of the variable api_key on this query to run it.',
		)
	})

	// @feature permissions.error-is-text
	it('reads the sentence, not the traceback, to a System User', () => {
		const exc = `Traceback (most recent call last):\n  File "x.py"\nfrappe.exceptions.ValidationError: ${SENTENCE}`
		expect(getErrorMessage(refusal({ messages: [SENTENCE], exc }))).toBe(
			'Fill in the value of the variable api_key on this query to run it.',
		)
	})

	// @feature permissions.error-is-text
	it('reads the traceback when the server sent no sentence', () => {
		// frappe-ui's own placeholder when `_server_messages` is empty
		const exc = 'Traceback\npymysql.err.OperationalError: (1054, "Unknown column \'status\'")'
		expect(getErrorMessage(refusal({ messages: ['Internal Server Error'], exc }))).toBe(
			'(1054, "Unknown column \'status\'")',
		)
	})

	// @feature permissions.error-is-text
	it('keeps an escaped character a sentence names', () => {
		expect(
			getErrorMessage(
				refusal({ messages: ['<strong>R&amp;D &lt;2026&gt;</strong> is shared'] }),
			),
		).toBe('R&D <2026> is shared')
	})
})
