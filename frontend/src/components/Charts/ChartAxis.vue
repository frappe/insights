<template></template>

<script setup>
import { inject, watch } from 'vue'

const chartOptions = inject('options')
const $utils = inject('$utils')
const props = defineProps({ options: Object, default: () => ({}) })

watch(() => props.options, updateOptions, { deep: true, immediate: true })
function updateOptions(newOptions) {
	const { axisType, type = 'category', ...rest } = newOptions
	const defaults = {
		axisLabel: {
			formatter: function (value, index) {
				if (type === 'category') {
					return value
				}
				if (type === 'value') {
					return $utils.getShortNumber(value, 1)
				}
			},
		},
	}
	chartOptions[axisType] = { type, ...defaults, ...rest }
}
</script>
