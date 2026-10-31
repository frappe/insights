import { call } from 'frappe-ui'

// Only live source queries are capped server-side; cached and data store results
// come back without ever reaching the limiter. The client can't tell which path a
// query will take, so it doesn't try to stay under the server's limit - it fires up
// to a browser-friendly number at once and treats a rejection as "come back later".

const MAX_IN_FLIGHT = 6
const MAX_ATTEMPTS = 8
const RETRY_BASE_DELAY = 1000
// a rejected request still builds the query before the limiter turns it away, so it
// isn't free - back off to a steady interval instead of polling ever faster
const MAX_RETRY_DELAY = 8000

type Waiter = { priority: number; resume: () => void }

let inFlight = 0
const waiting: Waiter[] = []

// Each request is named, so the server can stop its query once nobody waits for
// it: the reader changed the filters, left the dashboard or left the page.
const REQUEST_ID_HEADER = 'X-Insights-Request-Id'
const CANCEL_METHOD = 'insights.api.view.cancel_queries'
const running = new Set<string>()
// A reload aborts the page's requests before it fires `pagehide`. The server
// still runs their queries, so a request that ends with no answer stays named
// a little longer, for the beacon.
const ABANDONED_REQUEST_MS = 5000

// `crypto.randomUUID` exists only on HTTPS and localhost, and a site may be
// served over plain HTTP
function newRequestId() {
	const bytes = crypto.getRandomValues(new Uint8Array(16))
	return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

let cancelling: string[] = []

/**
 * Ask the server to stop the queries of these requests. It answers nothing to
 * wait for. A dashboard that closes stops all its cards at once, so the ids
 * asked in one task go in one request.
 */
export function cancelQueryExecutions(requestIds: string[]) {
	if (!requestIds.length) return
	if (!cancelling.length) {
		queueMicrotask(() => {
			const request_ids = cancelling
			cancelling = []
			call(CANCEL_METHOD, { request_ids }).catch(() => {})
		})
	}
	cancelling.push(...requestIds)
}

// A page that unloads cannot wait for a request, so a beacon carries the ids.
// It cannot set headers, so the CSRF token goes in the form.
if (typeof window !== 'undefined') {
	window.addEventListener('pagehide', () => {
		if (!running.size) return
		const form = new FormData()
		form.append('request_ids', JSON.stringify([...running]))
		if (window.csrf_token) form.append('csrf_token', window.csrf_token)
		navigator.sendBeacon(`/api/method/${CANCEL_METHOD}`, form)
	})
}

class StaleExecutionError extends Error {}

function acquireSlot(priority: number): Promise<void> {
	if (inFlight < MAX_IN_FLIGHT) {
		inFlight++
		return Promise.resolve()
	}
	return new Promise((resume) => waiting.push({ priority, resume }))
}

function releaseSlot() {
	if (!waiting.length) {
		inFlight--
		return
	}

	let next = 0
	for (let i = 1; i < waiting.length; i++) {
		// strictly lower, so equal priorities keep their arrival order
		if (waiting[i].priority < waiting[next].priority) next = i
	}
	// hand the slot straight over, so it can't be taken by a caller that
	// arrives in between
	waiting.splice(next, 1)[0].resume()
}

export function isServerBusyError(err: any) {
	return err?.status === 503 && err?.exc_type === 'ServiceUnavailableError'
}

function retryDelay(attempt: number) {
	const delay = Math.min(RETRY_BASE_DELAY * 2 ** (attempt - 1), MAX_RETRY_DELAY)
	// jittered, so a batch of charts doesn't retry in lockstep
	return delay * (0.5 + Math.random())
}

/**
 * Run a server call once a slot is free, retrying while the server reports it is busy.
 *
 * The server rejects a busy query immediately, so the attempts below are what give a
 * chart time to wait its turn - together they keep trying for roughly 20-60s before
 * giving up and surfacing the error.
 *
 * `isStale` lets a superseded execution drop out instead of spending a slot on a
 * result nobody is waiting for. `signal` does that too, and once the request is
 * sent, aborting it asks the server to stop its query. `run` sends `headers`,
 * which name the request. `priority` orders the waiting calls, lowest first -
 * dashboard charts pass their position so the top of the page loads before the
 * bottom. Calls that are already running are not preempted.
 */
export async function scheduleQueryExecution<T>(
	run: (headers: Record<string, string>) => Promise<T>,
	options: { isStale?: () => boolean; priority?: number; signal?: AbortSignal } = {},
): Promise<T> {
	const { isStale, priority = 0, signal } = options

	for (let attempt = 1; ; attempt++) {
		await acquireSlot(priority)
		const requestId = newRequestId()
		const cancel = () => cancelQueryExecutions([requestId])
		let answered = true
		try {
			if (isStale?.() || signal?.aborted) throw new StaleExecutionError()
			running.add(requestId)
			signal?.addEventListener('abort', cancel, { once: true })
			return await run({ [REQUEST_ID_HEADER]: requestId })
		} catch (err: any) {
			answered = err?.status !== undefined || err instanceof StaleExecutionError
			if (attempt >= MAX_ATTEMPTS || !isServerBusyError(err)) throw err
		} finally {
			if (answered) running.delete(requestId)
			else setTimeout(() => running.delete(requestId), ABANDONED_REQUEST_MS)
			signal?.removeEventListener('abort', cancel)
			releaseSlot()
		}
		await new Promise((resolve) => setTimeout(resolve, retryDelay(attempt)))
	}
}
