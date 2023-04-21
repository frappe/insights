<script setup>
import { getShortNumber } from '@/utils'
import { computed } from 'vue'

const props = defineProps({
	chartData: { type: Object, required: true },
	options: { type: Object, required: true },
})

const results = computed(() => props.chartData.data)
const resultMap = computed(() => {
	if (!results.value?.length) return []
	const columns = results.value[0].map((d) => d.label)
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
		return getShortNumber(value, props.options.decimals)
	}
	return Number(value).toLocaleString(undefined, {
		maximumFractionDigits: props.options.decimals,
	})
}

const progressPercent = computed(() => {
	const percent = ((progress.value * 100) / target.value).toFixed(2)
	return percent > 100 ? 100 : percent < 0 ? 0 : percent
})
</script>

<template>
	<div
		v-if="props.options.title"
		class="flex h-full w-full items-center justify-center rounded-md p-6"
	>
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
	<template v-else>
		<slot name="placeholder"></slot>
	</template>
</template>
