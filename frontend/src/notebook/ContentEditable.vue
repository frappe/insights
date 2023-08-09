<template>
	<component
		:is="tag"
		class="contenteditable align-middle outline-none transition-all before:text-gray-500"
		:contenteditable="disabled ? false : contenteditable"
		:placeholder="placeholder"
		@input="update"
		@blur="update"
		@paste="onPaste"
		@keypress="onKeypress"
		ref="element"
		spellcheck="false"
	>
	</component>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'

function replaceAll(str, search, replacement) {
	return str.split(search).join(replacement)
}

const emit = defineEmits(['returned', 'update:modelValue', 'change'])
const props = defineProps({
	tag: {
		type: String,
		default: 'div',
	},
	contenteditable: {
		type: [Boolean, String],
		default: true,
	},
	disabled: {
		type: Boolean,
		default: false,
	},
	modelValue: String | Number,
	value: String | Number,
	placeholder: String,
	noHtml: {
		type: Boolean,
		default: true,
	},
	noNl: {
		type: Boolean,
		default: true,
	},
})

const element = ref()

function currentContent() {
	return props.noHtml ? element.value?.innerText : element.value?.innerHTML
}

function updateContent(newcontent) {
	if (props.noHtml) {
		element.value.innerText = newcontent
	} else {
		element.value.innerHTML = newcontent
	}
}

function valuePropPresent() {
	return props.value != undefined
}

function update(event) {
	if (valuePropPresent()) {
		emit('change', currentContent())
	} else {
		emit('update:modelValue', currentContent())
	}
}

function onPaste(event) {
	event.preventDefault()
	let text = (event.originalEvent || event).clipboardData.getData('text/plain')
	if (props.noNl) {
		text = replaceAll(text, '\r\n', ' ')
		text = replaceAll(text, '\n', ' ')
		text = replaceAll(text, '\r', ' ')
	}
	window.document.execCommand('insertText', false, text)
}
function onKeypress(event) {
	if (event.key == 'Enter' && props.noNl) {
		event.preventDefault()
		emit('returned', currentContent())
	}
}

onMounted(() => {
	updateContent(valuePropPresent() ? props.value : props.modelValue ?? '')
})

watch(
	() => props.modelValue ?? props.value,
	(newval, oldval) => {
		if (newval != currentContent()) {
			updateContent(newval ?? '')
		}
	}
)

watch(
	() => props.noHtml,
	(newval, oldval) => {
		updateContent(props.modelValue ?? '')
	}
)

watch(
	() => props.tag,
	(newval, oldval) => {
		updateContent(props.modelValue ?? '')
	},
	{ flush: 'post' }
)
</script>

<style lang="scss">
.contenteditable:empty:before {
	content: attr(placeholder);
	pointer-events: none;
	display: block; /* For Firefox */
}
</style>
