<script setup>
import { computed, inject } from 'vue'
const props = defineProps({
	data: {
		type: Object,
		required: true,
	},
	options: {
		type: Object,
		default: {},
	},
})
const $utils = inject('$utils')

const formattedValue = computed(() => {
	let value = props.data.value || 0
	value = $utils.getShortNumber(value, props.options.decimals)
	return value
})

const prefix = computed(() => {
	return props.options.prefix || ''
})
const suffix = computed(() => {
	return props.options.suffix || ''
})
</script>

<template>
	<div class="h-full w-full rounded-md border py-5">
		<div class="mx-auto flex h-full w-fit min-w-40 flex-col justify-center">
			<div
				:title="props.data.title"
				class="w-full overflow-hidden text-ellipsis whitespace-nowrap text-base text-gray-600"
			>
				{{ props.data.title }}
			</div>
			<div class="text-[38px] leading-tight">
				{{ prefix }}{{ formattedValue }}{{ suffix }}
			</div>
		</div>
	</div>
</template>
