<template>
	<!-- Dressed like frappe-ui's TextInput: the same size and variant tables,
	     with `focus-within` where the input says `focus`, because the element
	     that takes focus is the text inside. The box carries the caller's
	     classes and the prefix sits inside it like an input's own. -->
	<div :class="boxClasses">
		<slot name="prefix" />
		<component
			:is="tag"
			class="contenteditable min-w-0 flex-1 truncate outline-none before:text-ink-gray-4"
			:contenteditable="disabled ? false : contenteditable"
			:placeholder="placeholder"
			@input="update"
			@blur="update('blur')"
			@paste="onPaste"
			@keypress="onKeypress"
			ref="element"
			spellcheck="false"
		>
		</component>
		<slot name="suffix" />
	</div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

function replaceAll(str, search, replacement) {
	return str.split(search).join(replacement)
}

const emit = defineEmits(['returned', 'update:modelValue', 'change', 'blur'])
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
	variant: {
		type: String,
		default: 'ghost',
	},
	size: {
		type: String,
		default: 'sm',
	},
})

// Copied from frappe-ui TextInput, `focus:` rewritten as `focus-within:`.
// `useInputClasses` now publishes these tables with the focus prefix as an
// argument, but not in a shape this box can take: its `ghost` draws no focus
// ring, and its sizes carry a font-size. Font-size is left out here on purpose,
// because the caller's text style owns type and a `text-base` would outrank a
// frappe-ui component class like `text-lg-semibold`. See
// docs/projects/table-experience/issues/07-frappe-ui-gaps.md
const sizeClasses = {
	// gaps assume the 14px icon every input in this app draws, so the text
	// starts where TextInput's `ps-8` / `ps-9` / `ps-10` puts it
	sm: 'rounded-4 h-7 px-2 gap-2.5',
	md: 'rounded-4 h-8 px-2.5 gap-3',
	lg: 'rounded-5 h-10 px-3 gap-3',
	xl: 'rounded-5 h-10 px-3 gap-3',
}
const variantClasses = {
	subtle: 'border border-[--surface-gray-2] bg-surface-gray-2 hover:border-outline-elevation-2 hover:bg-surface-gray-3 focus-within:bg-surface-base focus-within:border-outline-gray-4 focus-within:shadow-sm',
	outline:
		'border border-outline-gray-2 bg-surface-base hover:border-outline-gray-3 hover:shadow-sm focus-within:bg-surface-base focus-within:border-outline-gray-4 focus-within:shadow-sm',
	// the border is always there, transparent at rest, so focus only recolors
	// it — the same motion the input makes, and nothing shifts
	ghost: 'border border-transparent bg-transparent focus-within:border-outline-gray-4 focus-within:bg-surface-base focus-within:shadow-sm',
	// a read-only title is not a disabled input: it keeps the ink it inherits
	disabled: 'border border-transparent bg-transparent',
}
const boxClasses = computed(() => [
	'inline-flex min-w-0 items-center transition-colors',
	sizeClasses[props.size] || sizeClasses.sm,
	variantClasses[props.disabled ? 'disabled' : props.variant] || variantClasses.ghost,
	props.disabled ? '' : 'text-ink-gray-8',
])

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

function emitContent(value) {
	if (valuePropPresent()) {
		emit('change', value)
	} else {
		emit('update:modelValue', value)
	}
}

function update(event) {
	if (event == 'blur') {
		emit('blur', currentContent())
	}
	emitContent(currentContent())
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

function isFocused() {
	return document.activeElement === element.value
}

watch(
	() => props.modelValue ?? props.value,
	(newval) => {
		if (!isFocused() && newval != currentContent()) {
			updateContent(newval ?? '')
		}
	},
)

watch(
	() => props.noHtml,
	() => {
		updateContent(props.modelValue ?? '')
	},
)

watch(
	() => props.tag,
	() => {
		updateContent(props.modelValue ?? '')
	},
	{ flush: 'post' },
)
</script>

<style>
.contenteditable:empty:before {
	content: attr(placeholder);
	pointer-events: none;
	display: block; /* For Firefox */
}
</style>
