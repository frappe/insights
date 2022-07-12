export function isEmptyObj(object) {
	if (object === null || object === undefined) {
		return true
	}
	return Object.keys(object).length === 0
}

export function safeJSONParse(str, defaultValue = null) {
	if (str === null || str === undefined) {
		return defaultValue
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
