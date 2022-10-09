<template></template>

<script setup>
import { inject, useAttrs, watch } from 'vue'

const { axisType, type = 'category', ...attributes } = useAttrs()
const options = inject('options')
const $utils = inject('$utils')
const convertAttributesToOptions = inject('convertAttributesToOptions')

const defaults = {
	axisLabel: {
		formatter: function (value, index) {
			if (type === 'category') {
				return value
			}
			if (type === 'value') {
				return $utils.getShortNumber(value)
			}
		},
	},
}

watch(() => attributes, updateOptions, { deep: true, immediate: true })
function updateOptions(newAttributes) {
	const optionsObject = convertAttributesToOptions(newAttributes)
	options[axisType] = { type, ...defaults, ...optionsObject }
}
</script>
