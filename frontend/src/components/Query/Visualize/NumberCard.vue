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
	// check if value has a decimal part
	if (value % 1 !== 0) {
		value = value.toFixed(1)
	}

	return $utils.getShortNumber(value)
})

const prefix = computed(() => {
	return props.options.prefix || ''
})
const suffix = computed(() => {
	return props.options.suffix || ''
})
</script>

<template>
	<div class="flex h-full w-full min-w-40 flex-col items-center justify-center px-2">
		<div class="text-[38px] leading-tight">{{ prefix }}{{ formattedValue }}{{ suffix }}</div>
		<div
			:title="props.data.title"
			class="w-full overflow-hidden text-ellipsis whitespace-nowrap text-center text-base text-gray-600"
		>
			{{ props.data.title }}
		</div>
	</div>
</template>
