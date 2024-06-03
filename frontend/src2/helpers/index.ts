
export function getUniqueId(length = 6) {
	return Date.now().toString().slice(-length)
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