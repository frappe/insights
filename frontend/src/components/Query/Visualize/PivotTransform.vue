<template>
	<div class="h-full w-full">
		<div class="h-7 text-base font-semibold text-gray-600">{{ props.title }}</div>
		<div class="flex w-full select-text flex-col pb-4 text-base">
			<div class="relative overflow-scroll rounded-md border scrollbar-hide">
				<div v-html="props.tableHtml"></div>
			</div>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	title: {
		type: String,
		default: '',
	},
	tableHtml: {
		type: String,
		required: true,
	},
})
</script>
