import { watch } from 'vue'

export const FIELDTYPES = {
	NUMBER: ['Integer', 'Decimal'],
	TEXT: ['Text', 'String'],
	DATE: ['Date', 'Datetime', 'Time'],
}

export function isEmptyObj(...args) {
	return args.some((arg) => {
		if (arg === null || arg === undefined) {
			return true
		}
		return Object.keys(arg).length === 0
	})
}

export function safeJSONParse(str, defaultValue = null) {
	if (str === null || str === undefined) {
		return defaultValue
	}

	if (typeof str === 'object') {
		return str
	}

	try {
		return JSON.parse(str)
	} catch (e) {
		console.groupCollapsed('Error parsing JSON')
		console.log(str)
		console.error(e)
		console.groupEnd()
		return defaultValue
	}
}

export function formatDate(value) {
	if (!value) {
		return ''
	}
	return new Date(value).toLocaleString('en-US', {
		month: 'short',
		year: 'numeric',
		day: 'numeric',
	})
}

export function isEqual(a, b) {
	if (a === b) {
		return true
	}
	if (Array.isArray(a) && Array.isArray(b)) {
		return a.length === b.length && a.every((item, index) => isEqual(item, b[index]))
	}
}

export function updateDocumentTitle(meta) {
	watch(
		() => meta,
		(meta) => {
			if (!meta.value.title) return
			if (meta.value.title && meta.value.subtitle) {
				document.title = `${meta.value.title} | ${meta.value.subtitle}`
				return
			}
			if (meta.value.title) {
				document.title = `${meta.value.title} | Frappe Insights`
				return
			}
		},
		{ immediate: true, deep: true }
	)
}

export function fuzzySearch(arr, { term, keys }) {
	// search for term in all keys of arr items and sort by relevance
	const lowerCaseTerm = term.toLowerCase()
	const results = arr.reduce((acc, item) => {
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

export function ellipsis(value, length) {
	if (value && value.length > length) {
		return value.substring(0, length) + '...'
	}
	return value
}

export default {
	isEmptyObj,
	safeJSONParse,
	formatDate,
	isEqual,
	updateDocumentTitle,
	fuzzySearch,
}
