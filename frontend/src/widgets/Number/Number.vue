<script setup>
import { computed, inject } from 'vue'

const $utils = inject('$utils')
const props = defineProps({
	chartData: { type: Object, required: true },
	options: { type: Object, required: true },
})

const results = computed(() => {
	return props.chartData.data
})
const formattedValue = computed(() => {
	console.log('results.value', results.value)
	if (!results.value?.length) return
	if (!props.options.column) return
	const columnIndex = results.value[0].findIndex((header) => {
		return header.split('::')[0] === props.options.column
	})
	const _value = results.value.slice(1).reduce((acc, row) => {
		return acc + row[columnIndex]
	}, 0)
	return $utils.getShortNumber(_value, props.options.decimals)
})
</script>

<template>
	<div v-if="formattedValue" class="h-full w-full overflow-hidden py-5 px-8">
		<div class="mx-auto flex h-full w-full min-w-40 flex-col justify-center overflow-hidden">
			<div
				class="w-full overflow-hidden text-ellipsis whitespace-nowrap text-base text-gray-600"
			>
				{{ props.options.title }}
			</div>
			<div class="text-[34px] leading-tight">
				{{ props.options.prefix }}{{ formattedValue }}{{ props.options.suffix }}
			</div>
		</div>
	</div>
	<div v-else>
		<slot name="placeholder"></slot>
	</div>
</template>
