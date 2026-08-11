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
 * result nobody is waiting for. `priority` orders the waiting calls, lowest first -
 * dashboard charts pass their position so the top of the page loads before the
 * bottom. Calls that are already running are not preempted.
 */
export async function scheduleQueryExecution<T>(
	run: () => Promise<T>,
	options: { isStale?: () => boolean; priority?: number } = {},
): Promise<T> {
	const { isStale, priority = 0 } = options

	for (let attempt = 1; ; attempt++) {
		await acquireSlot(priority)
		try {
			if (isStale?.()) throw new StaleExecutionError()
			return await run()
		} catch (err) {
			if (attempt >= MAX_ATTEMPTS || !isServerBusyError(err)) throw err
		} finally {
			releaseSlot()
		}
		await new Promise((resolve) => setTimeout(resolve, retryDelay(attempt)))
	}
}
