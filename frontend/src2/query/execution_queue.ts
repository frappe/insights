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

let inFlight = 0
const waiting: Array<() => void> = []

class StaleExecutionError extends Error {}

function acquireSlot(): Promise<void> {
	if (inFlight < MAX_IN_FLIGHT) {
		inFlight++
		return Promise.resolve()
	}
	return new Promise((resolve) => waiting.push(resolve))
}

function releaseSlot() {
	// hand the slot straight to the next in line, so it can't be taken by a
	// caller that arrives in between
	const next = waiting.shift()
	if (next) return next()
	inFlight--
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
 * result nobody is waiting for.
 */
export async function scheduleQueryExecution<T>(
	run: () => Promise<T>,
	isStale?: () => boolean,
): Promise<T> {
	for (let attempt = 1; ; attempt++) {
		await acquireSlot()
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
