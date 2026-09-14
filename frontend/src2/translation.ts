import { createResource } from 'frappe-ui'
import type { App } from 'vue'

function getTranslatedMessage(message: string): string {
	// Module-scope option lists call this while they are being defined, so it
	// runs wherever a module is loaded — including a test runner with no window.
	if (typeof window === 'undefined') return message
	const translatedMessages = (('translatedMessages' in window
		? window['translatedMessages']
		: null) ?? {}) as Record<string, string>
	return translatedMessages[message] || message
}

function translate(message: string): string
function translate(message: string, ...args: string[]): string
function translate(message: string, ...args: string[]): string {
	const translatedMessage = getTranslatedMessage(message)
	if (args.length === 0) {
		return translatedMessage
	}
	return translatedMessage.replace(/{(\d+)}/g, function (match, index) {
		return typeof args[index] != 'undefined' ? args[index] : match
	})
}

export const __ = translate

/**
 * A table of translated strings, built when it is first read rather than when
 * the module defining it loads.
 *
 * Translations arrive asynchronously, so a `const` whose values are `__()` calls
 * is evaluated before any of them and stays English for the session. This reads
 * them at call time and rebuilds when a new set arrives.
 */
export function translatedTable<T>(build: () => T): () => T {
	let messages: unknown
	let table: T | undefined
	return () => {
		const current =
			typeof window === 'undefined' ? undefined : (window as any).translatedMessages
		if (table === undefined || messages !== current) {
			messages = current
			table = build()
		}
		return table
	}
}

function fetchTranslations() {
	createResource({
		url: 'insights.api.translations.get_translations',
		method: 'GET',
		cache: 'translations',
		auto: true,
		transform(data: Record<string, string>) {
			;(window as any).translatedMessages = data
		},
	})
}

export function translationPlugin(app: App<Element>) {
	app.config.globalProperties.__ = translate
	const windowObj = window as any
	windowObj.__ = translate
	if (!windowObj.translatedMessages) {
		fetchTranslations()
	}
}

declare module '@vue/runtime-core' {
	interface ComponentCustomProperties {
		__: typeof translate
	}
}
