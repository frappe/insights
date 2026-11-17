import type { APIRequestContext, APIResponse } from '@playwright/test'

/**
 * REST access to a Frappe site. Adapted from frappe/wiki's e2e/helpers/frappe.ts.
 *
 * Wiki reads one CSRF token from one file into one module-level cache. This
 * suite logs in as two roles, and a CSRF token belongs to a single session, so
 * the token is bound to the client instead of cached globally.
 */

/**
 * The two statuses Frappe uses to mean "retry later", and nothing else.
 *
 * 503 is `QueueOverloaded`, raised when the bench's background queue is over
 * `max_queued_jobs`. Every write that enqueues a job gets it, and a Workbook
 * delete enqueues one per document it cascades to. 508 is `QueryDeadlockError`,
 * which the framework documents as "a concurrent transaction is blocking this
 * one, retry later". Both clear on their own, so a seeding call that gives up
 * on the first one fails a test for a reason the test is not about.
 */
const RETRY_STATUSES = [503, 508]
const RETRY_ATTEMPTS = 8

function backoffDelay(attempt: number): number {
	// Jittered, so parallel workers that all bounced off the same overloaded
	// queue do not come back in step. 8 attempts span roughly 30 seconds.
	const base = Math.min(250 * 2 ** attempt, 8_000)
	return base / 2 + Math.random() * (base / 2)
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Send a request, and send it again while Frappe answers "retry later". */
async function sendWithRetry(send: () => Promise<APIResponse>): Promise<APIResponse> {
	let response = await send()

	for (let attempt = 0; attempt < RETRY_ATTEMPTS; attempt++) {
		if (!RETRY_STATUSES.includes(response.status())) {
			return response
		}
		await sleep(backoffDelay(attempt))
		response = await send()
	}

	return response
}

export interface FrappeResponse<T = unknown> {
	message?: T
	exc?: string
	exc_type?: string
	_server_messages?: string
}

export type ListOptions = {
	fields?: string[]
	filters?: Record<string, unknown>
	limit?: number
	orderBy?: string
}

export interface FrappeApi {
	createDoc<T = Record<string, unknown>>(
		doctype: string,
		doc: Record<string, unknown>,
	): Promise<T>
	getDoc<T = Record<string, unknown>>(doctype: string, name: string): Promise<T>
	updateDoc<T = Record<string, unknown>>(
		doctype: string,
		name: string,
		updates: Record<string, unknown>,
	): Promise<T>
	deleteDoc(doctype: string, name: string): Promise<void>
	getList<T = Record<string, unknown>>(doctype: string, options?: ListOptions): Promise<T[]>
	callMethod<T = unknown>(method: string, args?: Record<string, unknown>): Promise<T>
	docExists(doctype: string, name: string): Promise<boolean>
	uploadFile(fileName: string, content: string): Promise<UploadedFile>
}

/** What `/api/method/upload_file` returns. `name` is the File document. */
export type UploadedFile = { name: string; file_name: string; file_url: string }

export function createFrappeApi(request: APIRequestContext, csrfToken: string): FrappeApi {
	if (!csrfToken) {
		// Frappe answers a write without the header with an opaque 417, so refuse
		// here rather than let every seeding call fail with the same blank error.
		throw new Error('createFrappeApi needs a CSRF token')
	}

	const csrfHeader: Record<string, string> = { 'X-Frappe-CSRF-Token': csrfToken }
	const writeHeaders: Record<string, string> = {
		'Content-Type': 'application/json',
		...csrfHeader,
	}

	async function createDoc<T = Record<string, unknown>>(
		doctype: string,
		doc: Record<string, unknown>,
	): Promise<T> {
		const response = await sendWithRetry(() =>
			request.post(`/api/resource/${doctype}`, { data: doc, headers: writeHeaders }),
		)

		if (!response.ok()) {
			throw new Error(`Failed to create ${doctype}: ${await response.text()}`)
		}

		const result = await response.json()
		return result.data as T
	}

	async function getDoc<T = Record<string, unknown>>(doctype: string, name: string): Promise<T> {
		const response = await sendWithRetry(() =>
			request.get(`/api/resource/${doctype}/${encodeURIComponent(name)}`),
		)

		if (!response.ok()) {
			throw new Error(`Failed to get ${doctype}/${name}: ${await response.text()}`)
		}

		const result = await response.json()
		return result.data as T
	}

	async function updateDoc<T = Record<string, unknown>>(
		doctype: string,
		name: string,
		updates: Record<string, unknown>,
	): Promise<T> {
		const response = await sendWithRetry(() =>
			request.put(`/api/resource/${doctype}/${encodeURIComponent(name)}`, {
				data: updates,
				headers: writeHeaders,
			}),
		)

		if (!response.ok()) {
			throw new Error(`Failed to update ${doctype}/${name}: ${await response.text()}`)
		}

		const result = await response.json()
		return result.data as T
	}

	async function deleteDoc(doctype: string, name: string): Promise<void> {
		const response = await sendWithRetry(() =>
			request.delete(`/api/resource/${doctype}/${encodeURIComponent(name)}`, {
				headers: csrfHeader,
			}),
		)

		if (!response.ok()) {
			throw new Error(`Failed to delete ${doctype}/${name}: ${await response.text()}`)
		}
	}

	async function getList<T = Record<string, unknown>>(
		doctype: string,
		options: ListOptions = {},
	): Promise<T[]> {
		const params = new URLSearchParams()

		if (options.fields) {
			params.set('fields', JSON.stringify(options.fields))
		}
		if (options.filters) {
			params.set('filters', JSON.stringify(options.filters))
		}
		if (options.limit !== undefined) {
			// 0 means "no limit" in Frappe — without this, the REST default of 20
			// silently truncates large result sets.
			params.set('limit_page_length', options.limit.toString())
		}
		if (options.orderBy) {
			params.set('order_by', options.orderBy)
		}

		const response = await sendWithRetry(() =>
			request.get(`/api/resource/${doctype}?${params.toString()}`),
		)

		if (!response.ok()) {
			throw new Error(`Failed to get list of ${doctype}: ${await response.text()}`)
		}

		const result = await response.json()
		return result.data as T[]
	}

	async function callMethod<T = unknown>(
		method: string,
		args: Record<string, unknown> = {},
	): Promise<T> {
		const response = await sendWithRetry(() =>
			request.post(`/api/method/${method}`, { data: args, headers: writeHeaders }),
		)

		if (!response.ok()) {
			throw new Error(`Failed to call ${method}: ${await response.text()}`)
		}

		const result: FrappeResponse<T> = await response.json()
		return result.message as T
	}

	async function docExists(doctype: string, name: string): Promise<boolean> {
		try {
			await getDoc(doctype, name)
			return true
		} catch {
			return false
		}
	}

	/**
	 * Upload a file the way the browser does, as multipart.
	 *
	 * Insights reads an uploaded CSV by File document name, so a flow that seeds
	 * an upload needs the real upload route and not a File row written over
	 * REST. The file is private, which is what the upload dialog sends.
	 */
	async function uploadFile(fileName: string, content: string): Promise<UploadedFile> {
		const response = await sendWithRetry(() =>
			request.post('/api/method/upload_file', {
				headers: csrfHeader,
				multipart: {
					is_private: '1',
					file_name: fileName,
					file: { name: fileName, mimeType: 'text/csv', buffer: Buffer.from(content) },
				},
			}),
		)

		if (!response.ok()) {
			throw new Error(`Failed to upload ${fileName}: ${await response.text()}`)
		}

		const result: FrappeResponse<UploadedFile> = await response.json()
		return result.message as UploadedFile
	}

	return { createDoc, getDoc, updateDoc, deleteDoc, getList, callMethod, docExists, uploadFile }
}
