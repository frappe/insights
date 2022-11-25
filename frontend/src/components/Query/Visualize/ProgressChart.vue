<script setup>
import { computed, inject } from 'vue'

const props = defineProps({
	title: String,
	progress: Number,
	target: Number,
	options: Object,
})

const $utils = inject('$utils')

const formattedProgress = computed(() => {
	if (props.options.shorten) {
		return $utils.getShortNumber(props.progress, props.options.decimals)
	}
	return Number(props.progress).toLocaleString(undefined, {
		maximumFractionDigits: props.options.decimals,
	})
})
const formattedTarget = computed(() => {
	if (props.options.shorten) {
		return $utils.getShortNumber(props.target, props.options.decimals)
	}
	return Number(props.target).toLocaleString(undefined, {
		maximumFractionDigits: props.options.decimals,
	})
})
const progressPercent = computed(() => {
	return ((props.progress * 100) / props.target).toFixed(2)
})

const prefix = computed(() => {
	return props.options.prefix || ''
})
const suffix = computed(() => {
	return props.options.suffix || ''
})
</script>

<template>
	<div class="flex h-full w-full items-center justify-center rounded-md border p-4">
		<div class="h-fit w-full max-w-[22rem]">
			<div>
				<div class="text-gray-500">{{ props.title }}</div>
				<div class="text-[34px] font-medium leading-tight tracking-wide">
					{{ prefix }}{{ formattedProgress }}{{ suffix }}
				</div>
			</div>
			<div class="mb-1">
				<div class="mt-2 flex justify-between text-sm tracking-wide text-gray-500">
					<div>{{ progressPercent }}%</div>
					<div>{{ prefix }}{{ formattedTarget }}{{ suffix }}</div>
				</div>
				<div class="mt-1 rounded-full bg-blue-100">
					<div
						class="h-2 rounded-full bg-blue-500"
						:style="{ width: progressPercent > 100 ? '100%' : progressPercent + '%' }"
					></div>
				</div>
			</div>
		</div>
	</div>
</template>
