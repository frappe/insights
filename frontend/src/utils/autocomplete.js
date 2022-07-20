import { nextTick } from 'vue'

export function autocompleteSquareBrackets(inputElement, modelValue) {
	if (!inputElement) {
		return
	}

	// if a user types open square brackets, we want to autocomplete them with close square brackets
	inputElement.addEventListener('keyup', function (e) {
		// check if any modifiers are pressed
		const modifiers = [e.ctrlKey, e.altKey, e.shiftKey, e.metaKey]
		if (modifiers.some(Boolean)) {
			return
		}

		const caretPosition = e.target.selectionStart
		if (e.keyCode === 219) {
			// if open square bracket button is clicked,
			// append close square bracket after caret position
			modelValue.value =
				modelValue.value.slice(0, caretPosition) +
				']' +
				modelValue.value.slice(caretPosition)
			nextTick(() => {
				// set caret position before close square bracket
				e.target.setSelectionRange(caretPosition, caretPosition)
			})
		}
	})
	inputElement.addEventListener('keydown', function (e) {
		// check if any modifiers are pressed
		const modifiers = [e.ctrlKey, e.altKey, e.shiftKey, e.metaKey]
		if (modifiers.some(Boolean)) {
			return
		}

		// if backspace is pressed,
		if (e.keyCode === 8) {
			// if backspace is pressed,
			// check if deleted character is an open square bracket
			// if yes, remove close square bracket after caret position
			const caretPosition = e.target.selectionStart
			const deleted_character = modelValue.value.slice(caretPosition - 1, caretPosition)
			if (deleted_character === '[' && modelValue.value.charAt(caretPosition) === ']') {
				nextTick(() => {
					modelValue.value =
						modelValue.value.slice(0, caretPosition - 1) +
						modelValue.value.slice(caretPosition + 1)
				})
			}
		}
	})
}

export function autocompleteQuotes(inputElement, modelValue) {
	if (!inputElement) {
		return
	}

	inputElement.addEventListener('keyup', function (e) {
		// check if any modifiers are pressed except shift
		const modifiers = [e.ctrlKey, e.altKey, e.metaKey]
		if (modifiers.some(Boolean)) {
			return
		}

		if (e.keyCode === 222 && e.shiftKey) {
			// if open quote button is clicked,
			// append close quote after caret position
			const caretPosition = e.target.selectionStart
			modelValue.value =
				modelValue.value.slice(0, caretPosition) +
				'"' +
				modelValue.value.slice(caretPosition)
			nextTick(() => {
				// set caret position before close quote
				e.target.setSelectionRange(caretPosition, caretPosition)
			})
		}
	})

	inputElement.addEventListener('keydown', function (e) {
		// check if any modifiers are pressed except shift
		const modifiers = [e.ctrlKey, e.altKey, e.metaKey]
		if (modifiers.some(Boolean)) {
			return
		}

		// if backspace is pressed,
		if (e.keyCode === 8) {
			// if backspace is pressed,
			// check if deleted character is an open square bracket
			// if yes, remove close square bracket after caret position
			const caretPosition = e.target.selectionStart
			const deleted_character = modelValue.value.slice(caretPosition - 1, caretPosition)
			if (deleted_character === '"' && modelValue.value.charAt(caretPosition) === '"') {
				nextTick(() => {
					modelValue.value =
						modelValue.value.slice(0, caretPosition - 1) +
						modelValue.value.slice(caretPosition + 1)
				})
			}
		}
	})
}
