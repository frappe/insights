<script setup>
import { computed, inject } from 'vue'
import { whenever } from '@vueuse/core'

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
const resultMap = computed(() => {
	if (!results.value?.length) return []
	const columns = results.value[0].map((d) => d.split('::')[0])
	return results.value.slice(1).map((row) => {
		const result = {}
		row.forEach((value, index) => {
			result[columns[index]] = value
		})
		return result
	})
})

const progress = computed(() => {
	if (!props.options.progress) return 0
	return resultMap.value.reduce((acc, row) => acc + row[props.options.progress], 0)
})

const target = computed(() => {
	if (!props.options.target) return 0
	if (props.options.targetType === 'Value') return parseInt(props.options.target)
	return resultMap.value.reduce((acc, row) => acc + row[props.options.target], 0)
})

function formatValue(value) {
	if (props.options.shorten) {
		return $utils.getShortNumber(value, props.options.decimals)
	}
	return Number(value).toLocaleString(undefined, {
		maximumFractionDigits: props.options.decimals,
	})
}

const progressPercent = computed(() => {
	return ((progress.value * 100) / target.value).toFixed(2)
})
</script>

<template>
	<div class="flex h-full w-full items-center justify-center rounded-md border p-6">
		<div class="h-fit w-full max-w-[22rem]">
			<div>
				<div class="text-gray-500">{{ props.options.title }}</div>
				<div class="text-[34px] leading-tight">
					{{ props.options.prefix }}{{ formatValue(progress) }}{{ props.options.suffix }}
				</div>
			</div>
			<div class="mb-1">
				<div class="flex justify-between text-xs tracking-wide text-gray-500">
					<div>{{ progressPercent }}%</div>
					<div>
						{{ props.options.prefix }}{{ formatValue(target)
						}}{{ props.options.suffix }}
					</div>
				</div>
				<div class="mt-1 rounded-full bg-blue-100">
					<div
						class="h-1.5 rounded-full bg-blue-500"
						:style="{ width: progressPercent > 100 ? '100%' : progressPercent + '%' }"
					></div>
				</div>
			</div>
		</div>
	</div>
</template>
