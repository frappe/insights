import { watchDebounced } from '@vueuse/core'
import { watch } from 'vue'
import { createToast } from './toasts'

export function getUniqueId(length = 8) {
	return (+new Date() * Math.random()).toString(36).substring(0, length)
}

export function titleCase(str: string) {
	return str
		.toLowerCase()
		.split(' ')
		.map(function (word) {
			return word.charAt(0).toUpperCase() + word.slice(1)
		})
		.join(' ')
}

export function copy(obj: object) {
	return JSON.parse(JSON.stringify(obj))
}

export function waitUntil(fn: () => boolean) {
	return new Promise<void>((resolve) => {
		if (fn()) {
			resolve()
			return
		}
		const stop = watch(fn, (value) => {
			if (value) {
				stop()
				resolve()
			}
		})
	})
}

export function store<T>(key: string, value: () => T) {
	const stored = localStorage.getItem(key)
	watchDebounced(value, (val) => localStorage.setItem(key, JSON.stringify(val)), {
		debounce: 500,
		deep: true,
	})
	return stored ? JSON.parse(stored) : value()
}

export function getErrorMessage(err: any) {
	return err.exc?.split('\n').filter(Boolean).at(-1)
}

export function showErrorToast(err: Error) {
	createToast({
		variant: 'error',
		title: 'Error',
		message: getErrorMessage(err),
	})
	throw err
}