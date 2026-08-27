import type { APIRequestContext } from '@playwright/test'

/**
 * REST access to a Frappe site. Adapted from frappe/wiki's e2e/helpers/frappe.ts.
 *
 * Wiki reads one CSRF token from one file into one module-level cache. This
 * suite logs in as two roles, and a CSRF token belongs to a single session, so
 * the token is bound to the client instead of cached globally.
 */

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
}

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
		const response = await request.post(`/api/resource/${doctype}`, {
			data: doc,
			headers: writeHeaders,
		})

		if (!response.ok()) {
			throw new Error(`Failed to create ${doctype}: ${await response.text()}`)
		}

		const result = await response.json()
		return result.data as T
	}

	async function getDoc<T = Record<string, unknown>>(doctype: string, name: string): Promise<T> {
		const response = await request.get(`/api/resource/${doctype}/${encodeURIComponent(name)}`)

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
		const response = await request.put(`/api/resource/${doctype}/${encodeURIComponent(name)}`, {
			data: updates,
			headers: writeHeaders,
		})

		if (!response.ok()) {
			throw new Error(`Failed to update ${doctype}/${name}: ${await response.text()}`)
		}

		const result = await response.json()
		return result.data as T
	}

	async function deleteDoc(doctype: string, name: string): Promise<void> {
		const response = await request.delete(
			`/api/resource/${doctype}/${encodeURIComponent(name)}`,
			{
				headers: csrfHeader,
			},
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

		const response = await request.get(`/api/resource/${doctype}?${params.toString()}`)

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
		const response = await request.post(`/api/method/${method}`, {
			data: args,
			headers: writeHeaders,
		})

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

	return { createDoc, getDoc, updateDoc, deleteDoc, getList, callMethod, docExists }
}
