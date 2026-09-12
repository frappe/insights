<template>
	<!-- A title that edits in place: no chrome at rest, and on focus the chrome
	     frappe-ui's outline input draws, on the box because the element that
	     takes focus is the text inside it. Font-size is the caller's, so a
	     `text-lg-semibold` on this component is not fought by one here. -->
	<div :class="boxClasses">
		<slot name="prefix" />
		<div
			class="contenteditable min-w-0 flex-1 truncate outline-none before:text-ink-gray-4"
			:contenteditable="!disabled"
			:placeholder="placeholder"
			@input="update"
			@blur="update('blur')"
			@paste="onPaste"
			@keypress="onKeypress"
			ref="element"
			spellcheck="false"
		></div>
		<slot name="suffix" />
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

function replaceAll(str, search, replacement) {
	return str.split(search).join(replacement)
}

const emit = defineEmits(['returned', 'update:modelValue', 'blur'])
const props = defineProps({
	disabled: {
		type: Boolean,
		default: false,
	},
	modelValue: String | Number,
	placeholder: String,
})

const boxClasses = computed(() => [
	'inline-flex h-7 min-w-0 items-center gap-2.5 rounded-4 border border-transparent bg-transparent px-2 transition-colors',
	// a read-only title is not a disabled input: it keeps the ink it inherits
	props.disabled
		? ''
		: 'text-ink-gray-8 focus-within:border-outline-gray-4 focus-within:bg-surface-base focus-within:shadow-sm',
])

const element = ref()

function currentContent() {
	return element.value?.innerText
}

function updateContent(newcontent) {
	element.value.innerText = newcontent
}

function update(event) {
	if (event == 'blur') {
		emit('blur', currentContent())
	}
	emit('update:modelValue', currentContent())
}

// A title is one line, so a pasted newline joins and Enter commits instead of
// breaking.
function onPaste(event) {
	event.preventDefault()
	let text = (event.originalEvent || event).clipboardData.getData('text/plain')
	text = replaceAll(text, '\r\n', ' ')
	text = replaceAll(text, '\n', ' ')
	text = replaceAll(text, '\r', ' ')
	window.document.execCommand('insertText', false, text)
}

function onKeypress(event) {
	if (event.key == 'Enter') {
		event.preventDefault()
		emit('returned', currentContent())
	}
}

onMounted(() => updateContent(props.modelValue ?? ''))

function isFocused() {
	return document.activeElement === element.value
}

watch(
	() => props.modelValue,
	(newval) => {
		if (!isFocused() && newval != currentContent()) {
			updateContent(newval ?? '')
		}
	},
)
</script>

<style>
.contenteditable:empty:before {
	content: attr(placeholder);
	pointer-events: none;
	display: block; /* For Firefox */
}
</style>
