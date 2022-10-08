<script setup>
import { computed } from 'vue'
const props = defineProps({
	value: {
		type: Number,
	},
	options: {
		type: Object,
		default: {},
	},
})
const formattedValue = computed(() => {
	let value = props.value || 0
	// check if value has a decimal part
	if (value % 1 !== 0) {
		value = value.toFixed(1)
	}
	const locale = 'en-IN' // TODO: get locale from user settings
	let formatted = new Intl.NumberFormat(locale, {
		notation: 'compact',
	}).format(value)

	if (locale == 'en-IN') {
		formatted = formatted.replace('T', 'K')
	}

	return formatted
})

const prefix = computed(() => {
	return props.options.data.prefix || ''
})
const suffix = computed(() => {
	return props.options.data.suffix || ''
})
</script>

<template>
	<div class="flex h-full w-full min-w-40 flex-col items-center justify-center">
		<div class="text-[38px] leading-tight">{{ prefix }}{{ formattedValue }}{{ suffix }}</div>
		<div class="text-[14px] font-light">{{ props.options.title }}</div>
	</div>
</template>
