import { watchDebounced } from '@vueuse/core'
import domtoimage from 'dom-to-image'
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

export function copy<T>(obj: T) {
	return JSON.parse(JSON.stringify(obj)) as T
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

export function downloadImage(
	element: HTMLElement,
	filename: string,
	scale = 1,
	options = {}
) {
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
