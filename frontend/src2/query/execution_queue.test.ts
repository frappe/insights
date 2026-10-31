import { afterEach, describe, expect, it, vi } from 'vitest'

const calls = vi.hoisted(() => [] as { method: string; args: any }[])
vi.mock('frappe-ui', () => ({
	call: (method: string, args: any) => {
		calls.push({ method, args })
		return Promise.resolve()
	},
}))

// the queue listens for the page unloading as it loads
const page = vi.hoisted(() => {
	const listeners: Record<string, () => void> = {}
	;(globalThis as any).window = {
		csrf_token: 'token',
		addEventListener: (type: string, listener: () => void) => (listeners[type] = listener),
	}
	return listeners
})

import { scheduleQueryExecution } from './execution_queue'

const REQUEST_ID_HEADER = 'X-Insights-Request-Id'

/** A request the server is still answering. */
function sent() {
	const request = {
		headers: {} as Record<string, string>,
		answer: (_: unknown) => {},
		fail: (_: unknown) => {},
	}
	const run = (headers: Record<string, string>) => {
		request.headers = headers
		return new Promise((resolve, reject) => {
			request.answer = resolve
			request.fail = reject
		})
	}
	return { request, run }
}

const settled = () => new Promise((resolve) => setTimeout(resolve, 0))

afterEach(() => {
	calls.length = 0
	vi.unstubAllGlobals()
})

describe('a query request nobody waits for', () => {
	// @feature data-store.cancel
	it('is named, and asks the server to stop its query when its reader aborts it', async () => {
		// a closed dashboard aborts all its cards at once, and they go in one request
		const cards = [sent(), sent()]
		const controller = new AbortController()
		const done = cards.map(({ run }) =>
			scheduleQueryExecution(run, { signal: controller.signal }),
		)
		await settled()
		const requestIds = cards.map(({ request }) => request.headers[REQUEST_ID_HEADER])
		expect(requestIds[0]).toMatch(/^[0-9a-f]{32}$/)

		controller.abort()
		cards.forEach(({ request }) => request.answer(undefined))
		await Promise.all(done)

		expect(calls).toEqual([
			{ method: 'insights.api.view.cancel_queries', args: { request_ids: requestIds } },
		])
	})

	// @feature data-store.cancel
	it('is named in a beacon to the server as the page unloads, with the CSRF token', async () => {
		const sendBeacon = vi.fn(() => true)
		vi.stubGlobal('navigator', { sendBeacon })
		const running = sent()
		const answered = sent()
		// a reload aborts the page's requests before it fires `pagehide`, and the
		// server runs on
		const aborted = sent()
		const queries = [
			scheduleQueryExecution(running.run),
			scheduleQueryExecution(answered.run),
			// eslint-disable-next-line no-restricted-syntax -- the aborted query is meant to fail; the test checks its cancel, not its result
			scheduleQueryExecution(aborted.run).catch(() => {}),
		]
		await settled()
		answered.request.answer({ rows: [] })
		aborted.request.fail(new TypeError('Failed to fetch'))
		await Promise.all(queries.slice(1))

		page.pagehide()

		expect(sendBeacon).toHaveBeenCalledOnce()
		const [url, form] = sendBeacon.mock.calls[0] as unknown as [string, FormData]
		expect(url).toBe('/api/method/insights.api.view.cancel_queries')
		expect(JSON.parse(form.get('request_ids') as string)).toEqual([
			running.request.headers[REQUEST_ID_HEADER],
			aborted.request.headers[REQUEST_ID_HEADER],
		])
		expect(form.get('csrf_token')).toBe('token')
		running.request.answer(undefined)
		await queries[0]
	})
})
