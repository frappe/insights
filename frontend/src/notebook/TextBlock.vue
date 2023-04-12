<script setup>
import { ref } from 'vue'
import ContentEditable from './ContentEditable.vue'
defineExpose({
	focus,
})
const emit = defineEmits(['change'])
const props = defineProps({
	block: {
		type: Object,
		required: true,
	},
})
const contentEditable = ref()
function focus(caretPosition) {
	contentEditable.value.$el.focus()
	if (!caretPosition) {
		moveCaretToEnd(contentEditable.value.$el)
	}
}
function moveCaretToEnd(el) {
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
</script>

<template>
	<ContentEditable
		ref="contentEditable"
		:class="[block.type, 'min-h-[1.5rem]']"
		v-model="block.content"
		placeholder="Type here..."
	>
	</ContentEditable>
</template>

<style scoped lang="scss">
.h1 {
	@apply mb-4 mt-5 text-7xl font-semibold;
}
.h2 {
	@apply mb-3 mt-4 text-5xl font-semibold;
}
.h3 {
	@apply mb-2 mt-3 text-3xl font-medium;
}
.p {
	@apply mb-3 mt-2 text-lg font-normal;
}
.blockquote {
	@apply mb-3 mt-2 border-l-4 border-gray-500 py-1 pl-3 text-lg font-normal leading-6 text-gray-600;
}
.divider {
	@apply pointer-events-none my-4 border-b-2;
	height: 0px !important;
	min-height: 1px !important;
}
</style>
