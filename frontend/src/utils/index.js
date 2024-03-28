import sessionStore from '@/stores/sessionStore'
import { createToast } from '@/utils/toasts'
import { watchDebounced } from '@vueuse/core'
import domtoimage from 'dom-to-image'
import { call } from 'frappe-ui'
import {
	Baseline,
	Calendar,
	CalendarClock,
	Clock,
	Hash,
	ShieldQuestion,
	ToggleLeft,
	Type,
} from 'lucide-vue-next'
import { computed, unref, watch } from 'vue'

export const COLUMN_TYPES = [
	{ label: 'String', value: 'String' },
	{ label: 'Integer', value: 'Integer' },
	{ label: 'Decimal', value: 'Decimal' },
	{ label: 'Text', value: 'Text' },
	{ label: 'Datetime', value: 'Datetime' },
	{ label: 'Date', value: 'Date' },
	{ label: 'Time', value: 'Time' },
]

export const fieldtypesToIcon = {
	Integer: Hash,
	Decimal: Hash,
	Date: Calendar,
	Datetime: CalendarClock,
	Time: Clock,
	Text: Type,
	String: Baseline,
	'Long Text': Type,
}

export const returnTypesToIcon = {
	number: Hash,
	string: Type,
	boolean: ToggleLeft,
	date: Calendar,
	datetime: CalendarClock,
	any: ShieldQuestion,
}

export const FIELDTYPES = {
	NUMBER: ['Integer', 'Decimal'],
	TEXT: ['Text', 'String'],
	DATE: ['Date', 'Datetime', 'Time'],
}

export const AGGREGATIONS = [
	{ label: 'Unique', value: 'group by', description: 'Group by' },
	{ label: 'Count of Records', value: 'count', description: 'Count' },
	{ label: 'Sum of', value: 'sum', description: 'Sum' },
	{ label: 'Average of', value: 'avg', description: 'Average' },
	{
		label: 'Cumulative Count of Records',
		value: 'cumulative count',
		description: 'Cumulative Count',
	},
	{ label: 'Cumulative Sum of', value: 'cumulative sum', description: 'Cumulative Sum' },
	{ label: 'Unique values of', value: 'distinct', description: 'Distinct' },
	{ label: 'Unique count of', value: 'distinct_count', description: 'Distinct Count' },
	{ label: 'Minimum of', value: 'min', description: 'Minimum' },
	{ label: 'Maximum of', value: 'max', description: 'Maximum' },
]

export const GRANULARITIES = [
	{ label: 'Minute', value: 'Minute', description: 'January 12, 2020 1:14 PM' },
	{ label: 'Hour', value: 'Hour', description: 'January 12, 2020 1:00 PM' },
	{ label: 'Hour of Day', value: 'Hour of Day', description: '1:00 PM' },
	{ label: 'Day', value: 'Day', description: '12th January, 2020' },
	{ label: 'Day Short', value: 'Day Short', description: '12th Jan, 20' },
	{ label: 'Week', value: 'Week', description: '12th January, 2020' },
	{ label: 'Month', value: 'Month', description: 'January, 2020' },
	{ label: 'Mon', value: 'Mon', description: 'Jan 20' },
	{ label: 'Quarter', value: 'Quarter', description: 'Q1, 2020' },
	{ label: 'Year', value: 'Year', description: '2020' },
	{ label: 'Day of Week', value: 'Day of Week', description: 'Monday' },
	{ label: 'Month of Year', value: 'Month of Year', description: 'January' },
	{ label: 'Quarter of Year', value: 'Quarter of Year', description: 'Q1' },
]

export function getOperatorOptions(columnType) {
	let options = [
		{ label: 'equals', value: '=' },
		{ label: 'not equals', value: '!=' },
		{ label: 'is', value: 'is' },
	]

	if (!columnType) {
		return options
	}

	if (FIELDTYPES.TEXT.includes(columnType)) {
		options = options.concat([
			{ label: 'contains', value: 'contains' },
			{ label: 'not contains', value: 'not_contains' },
			{ label: 'starts with', value: 'starts_with' },
			{ label: 'ends with', value: 'ends_with' },
			{ label: 'one of', value: 'in' },
			{ label: 'not one of', value: 'not_in' },
		])
	}
	if (FIELDTYPES.NUMBER.includes(columnType)) {
		options = options.concat([
			{ label: 'one of', value: 'in' },
			{ label: 'not one of', value: 'not_in' },
			{ label: 'greater than', value: '>' },
			{ label: 'smaller than', value: '<' },
			{ label: 'greater than equal to', value: '>=' },
			{ label: 'smaller than equal to', value: '<=' },
			{ label: 'between', value: 'between' },
		])
	}
	if (FIELDTYPES.DATE.includes(columnType)) {
		options = options.concat([
			{ label: 'greater than', value: '>' },
			{ label: 'smaller than', value: '<' },
			{ label: 'greater than equal to', value: '>=' },
			{ label: 'smaller than equal to', value: '<=' },
			{ label: 'between', value: 'between' },
			{ label: 'within', value: 'timespan' },
		])
	}
	return options
}

// a function to resolve the promise when a ref has a value
export async function whenHasValue(refOrGetter) {
	return new Promise((resolve) => {
		function onValue(value) {
			if (!value) return
			resolve(value)
			unwatch()
		}
		const unwatch = watch(refOrGetter, onValue, { deep: true })
		const value = typeof refOrGetter === 'function' ? refOrGetter() : unref(refOrGetter)
		onValue(value)
	})
}

export function isDimensionColumn(column) {
	return FIELDTYPES.TEXT.includes(column.type) || FIELDTYPES.DATE.includes(column.type)
}

export function moveCaretToEnd(el) {
	if (typeof window.getSelection != 'undefined' && typeof document.createRange != 'undefined') {
		var range = document.createRange()
		range.selectNodeContents(el)
		range.collapse(false)
		var sel = window.getSelection()
		sel.removeAllRanges()
		sel.addRange(range)
	} else if (typeof document.body.createTextRange != 'undefined') {
		var textRange = document.body.createTextRange()
		textRange.moveToElementText(el)
		textRange.collapse(false)
		textRange.select()
	}
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

export function getShortNumber(number, precision = 0) {
	const session = sessionStore()
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

export function formatNumber(number, precision = 2) {
	precision = precision || guessPrecision(number)
	const session = sessionStore()
	const locale = session.user?.country == 'India' ? 'en-IN' : session.user?.locale
	return new Intl.NumberFormat(locale || 'en-US', {
		maximumFractionDigits: precision,
	}).format(number)
}

export function guessPrecision(number) {
	// eg. 1.0 precision = 1, 1.00 precision = 2
	const str = number.toString()
	const decimalIndex = str.indexOf('.')
	if (decimalIndex === -1) return 0
	return Math.min(str.length - decimalIndex - 1, 2)
}

export async function getDataURL(type, data) {
	const blob = new Blob([data], { type })

	return new Promise((resolve) => {
		const fr = new FileReader()
		fr.addEventListener('loadend', () => {
			resolve(fr.result)
		})

		fr.readAsDataURL(blob)
	})
}

export async function convertFileToDataURL(file, type) {
	const buffer = await file.arrayBuffer()
	const array = new Uint8Array(buffer)
	return await getDataURL(type, array)
}

export function getQueryLink(table) {
	if (!table) return ''
	// returns a link to the query if the table is a query eg. Query Store queries
	if (table.startsWith('QRY')) {
		return `/insights/query/build/${table}`
	}
	return ''
}

export function copyToClipboard(text) {
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

export function setOrGet(obj, key, generator, generatorArgs) {
	if (!obj.hasOwnProperty(key)) {
		obj[key] = generator(...generatorArgs)
	}
	return obj[key]
}

export function useAutoSave(watchedFields, options = {}) {
	if (!options.saveFn) throw new Error('saveFn is required')

	const fields = computed(() => {
		if (!watchedFields.value) return
		return JSON.parse(JSON.stringify(watchedFields.value))
	})

	function saveIfChanged(newFields, oldFields) {
		if (!oldFields || !newFields) return
		if (JSON.stringify(newFields) == JSON.stringify(oldFields)) return
		options.saveFn()
	}

	const interval = options.interval || 1000
	watchDebounced(fields, saveIfChanged, {
		deep: true,
		debounce: interval,
	})
}

export function isInViewport(element) {
	if (!element) return false
	const rect = element.getBoundingClientRect()
	return (
		rect.top > 0 &&
		rect.left > 0 &&
		rect.bottom < (window.innerHeight || document.documentElement.clientHeight) &&
		rect.right < (window.innerWidth || document.documentElement.clientWidth)
	)
}

export function downloadImage(element, filename, options = {}) {
	return domtoimage
		.toBlob(element, {
			bgcolor: 'rgb(248, 248, 248)',
			...options,
		})
		.then(function (blob) {
			const link = document.createElement('a')
			link.download = filename
			link.href = URL.createObjectURL(blob)
			link.click()
		})
}
export function getImageSrc(element) {
	return domtoimage
		.toBlob(element, {
			bgcolor: 'rgb(248, 248, 248)',
		})
		.then((blob) => URL.createObjectURL(blob))
}

export function areDeeplyEqual(obj1, obj2) {
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

		if (keys1.length !== keys2.length || !keys1.every((key) => keys2.includes(key)))
			return false

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

export function createTaskRunner() {
	const queue = []
	let running = false
	const run = async () => {
		if (running) return
		running = true
		while (queue.length) {
			await queue.shift()()
		}
		running = false
	}
	return async (fn) => {
		queue.push(fn)
		await run()
	}
}

// a util function that is similar to watch but only runs the callback when the value is truthy and changes
export function wheneverChanges(getter, callback, options = {}) {
	let prevValue = null
	function onChange(value) {
		if (areDeeplyEqual(value, prevValue)) return
		if (!value) return
		prevValue = value
		callback(value)
	}
	return watch(getter, onChange, options)
}

export async function run_doc_method(method, doc, args = {}) {
	return call('run_doc_method', {
		method,
		dt: doc.doctype,
		dn: doc.name,
		args: args,
	})
}

export function makeColumnOption(column) {
	return {
		...column,
		description: column.type,
		value: `${column.table}.${column.column}`,
	}
}

export default {
	isEmptyObj,
	safeJSONParse,
	formatDate,
	isEqual,
	updateDocumentTitle,
	fuzzySearch,
	formatNumber,
	getShortNumber,
	copyToClipboard,
	ellipsis,
	areDeeplyEqual,
}
