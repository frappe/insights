<script setup>
import ContentEditable from '../ContentEditable.vue'
const emit = defineEmits(['change'])
const props = defineProps({
	block: {
		type: Object,
		required: true,
	},
})
</script>

<template>
	<ContentEditable
		v-model="block.content"
		placeholder="Type here..."
		:class="[block.type, 'focusable min-h-[1.5rem]']"
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
