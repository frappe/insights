<script setup>
import { computed, inject } from 'vue'
import { whenever } from '@vueuse/core'

const $utils = inject('$utils')
const props = defineProps({
	item_id: { required: true },
	options: { type: Object, required: true },
})

const dashboard = inject('dashboard')
whenever(
	() => props.options.query,
	() => dashboard.loadQueryResult(props.item_id, props.options.query),
	{ immediate: true }
)
const results = computed(() => {
	return dashboard.queryResults[`${props.item_id}-${props.options.query}`]
})
const formattedValue = computed(() => {
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
	<div class="h-full w-full overflow-hidden py-5 px-8">
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
</template>
