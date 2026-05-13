<script setup>
const props = defineProps({
	title: { type: String, required: false },
	title_font_size: { type: Number, default: 18 },
	title_color: { type: String, default: '#000000' },
})
</script>

<template>
	<div
		class="px-4 py-2 text-lg font-medium leading-6 text-gray-800"
		:style="{
			fontSize: (props.title_font_size || 18) + 'px',
			color: props.title_color || '#000000',
		}"
	>
		{{ title }}
	</div>
</template>
