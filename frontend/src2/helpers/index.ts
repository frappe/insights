import { watch } from 'vue'

export function getUniqueId(length = 6) {
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
