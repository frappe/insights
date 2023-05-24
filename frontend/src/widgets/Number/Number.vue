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
	if (!results.value?.length) return
	if (!props.options.column) return
	const columnIndex = results.value[0].findIndex((header) => {
		return header.label === props.options.column
	})
	const _value = results.value.slice(1).reduce((acc, row) => {
		return acc + row[columnIndex]
	}, 0)

	if (props.options.hasOwnProperty('shorten') && !props.options.shorten) {
		return $utils.formatNumber(_value, props.options.decimals)
	}
	return $utils.getShortNumber(_value, props.options.decimals)
})
</script>

<template>
	<div v-if="formattedValue" class="h-full w-full overflow-hidden px-8 py-5">
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
	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>
