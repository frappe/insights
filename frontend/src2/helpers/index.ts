import { watchDebounced } from '@vueuse/core'
import domtoimage from 'dom-to-image'
import { ComputedRef, Ref, watch } from 'vue'
import session from '../session'
import { DropdownOption, GroupedDropdownOption } from '../types/query.types'
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

export function copy<T>(obj: T) {
	return JSON.parse(JSON.stringify(obj)) as T
}

export function wheneverChanges(
	getter: Ref | ComputedRef | Function,
	callback: Function,
	options: any = {}
) {
	let prevValue: any
	function onChange(value: any) {
		if (areDeeplyEqual(value, prevValue)) return
		prevValue = value
		callback(value)
	}
	return watchDebounced(getter, onChange, options)
}

export function areDeeplyEqual(obj1: any, obj2: any): boolean {
	if (obj1 === obj2) return true

	if (Array.isArray(obj1) && Array.isArray(obj2)) {
		if (obj1.length !== obj2.length) return false

		return obj1.every((elem, index) => {
			return areDeeplyEqual(elem, obj2[index])
		})
	}

	if (typeof obj1 === 'object' && typeof obj2 === 'object' && obj1 !== null && obj2 !== null) {
		if (Array.isArray(obj1) || Array.isArray(obj2)) return false

		const keys1 = Object.keys(obj1)
		const keys2 = Object.keys(obj2)

		if (keys1.length !== keys2.length || !keys1.every((key) => keys2.includes(key))) return false

		for (let key in obj1) {
			let isEqual = areDeeplyEqual(obj1[key], obj2[key])
			if (!isEqual) {
				return false
			}
		}

		return true
	}

	return false
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

export function showErrorToast(err: Error, raise = true) {
	createToast({
		variant: 'error',
		title: 'Error',
		message: getErrorMessage(err),
	})
	if (raise) throw err
}

export function downloadImage(element: HTMLElement, filename: string, scale = 1, options = {}) {
	return domtoimage
		.toPng(element, {
			height: element.offsetHeight * scale,
			width: element.offsetWidth * scale,
			style: {
				transform: 'scale(' + scale + ')',
				transformOrigin: 'top left',
				width: element.offsetWidth + 'px',
				height: element.offsetHeight + 'px',
			},
			bgColor: 'white',
			...options,
		})
		.then(function (dataUrl: string) {
			const img = new Image()
			img.src = dataUrl
			img.onload = async () => {
				const link = document.createElement('a')
				link.download = filename
				link.href = img.src
				link.click()
			}
		})
}

export function formatNumber(number: number, precision = 2) {
	if (isNaN(number)) return number
	precision = precision || guessPrecision(number)
	const locale = session.user?.country == 'India' ? 'en-IN' : session.user?.locale
	return new Intl.NumberFormat(locale || 'en-US', {
		maximumFractionDigits: precision,
	}).format(number)
}

export function guessPrecision(number: number) {
	// eg. 1.0 precision = 1, 1.00 precision = 2
	const str = number.toString()
	const decimalIndex = str.indexOf('.')
	if (decimalIndex === -1) return 0
	return Math.min(str.length - decimalIndex - 1, 2)
}

export function getShortNumber(number: number, precision = 0) {
	const locale = session.user?.country == 'India' ? 'en-IN' : session.user?.locale
	let formatted = new Intl.NumberFormat(locale || 'en-US', {
		notation: 'compact',
		maximumFractionDigits: precision,
	}).format(number)

	if (locale == 'en-IN') {
		formatted = formatted.replace('T', 'K')
	}
	return formatted
}

export function fuzzySearch(arr: any[], { term, keys }: { term: string; keys: string[] }) {
	// search for term in all keys of arr items and sort by relevance
	const lowerCaseTerm = term.toLowerCase()
	type Result = { item: any; score: number }
	const results: Result[] = arr.reduce((acc, item) => {
		const score = keys.reduce((acc, key) => {
			const value = item[key]
			if (value) {
				const match = value.toLowerCase().indexOf(lowerCaseTerm)
				if (match !== -1) {
					return acc + match + 1
				}
			}
			return acc
		}, 0)
		if (score) {
			acc.push({ item, score })
		}
		return acc
	}, [])
	return results.sort((a, b) => a.score - b.score).map((item) => item.item)
}

export function safeJSONParse(str: string, defaultValue = null) {
	if (str === null || str === undefined) {
		return defaultValue
	}

	if (typeof str !== 'string') {
		return str
	}

	try {
		return JSON.parse(str)
	} catch (e) {
		console.groupCollapsed('Error parsing JSON')
		console.log(str)
		console.error(e)
		console.groupEnd()
		createToast({
			message: 'Error parsing JSON',
			variant: 'error',
		})
		return defaultValue
	}
}

export function copyToClipboard(text: string) {
	if (navigator.clipboard) {
		navigator.clipboard.writeText(text)
		createToast({
			variant: 'success',
			title: 'Copied to clipboard',
		})
	} else {
		// try to use execCommand
		const textArea = document.createElement('textarea')
		textArea.value = text
		textArea.style.position = 'fixed'
		document.body.appendChild(textArea)
		textArea.focus()
		textArea.select()
		try {
			document.execCommand('copy')
			createToast({
				variant: 'success',
				title: 'Copied to clipboard',
			})
		} catch (err) {
			createToast({
				variant: 'error',
				title: 'Copy to clipboard not supported',
			})
		} finally {
			document.body.removeChild(textArea)
		}
	}
}

export function ellipsis(value: string, length: number) {
	if (value && value.length > length) {
		return value.substring(0, length) + '...'
	}
	return value
}

export function flattenOptions(
	options: DropdownOption[] | GroupedDropdownOption[]
): DropdownOption[] {
	return 'group' in options[0]
		? (options as GroupedDropdownOption[]).map((c) => c.items).flat()
		: (options as DropdownOption[])
}
