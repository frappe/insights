<template></template>

<script setup>
import { inject, useAttrs, watch } from 'vue'

const attributes = useAttrs()
const options = inject('options')
const convertAttributesToOptions = inject('convertAttributesToOptions')

if (!options.series) {
	options.series = []
}

watch(() => attributes, updateOptions, { deep: true, immediate: true })

function updateOptions(newAttributes) {
	const optionsObject = convertAttributesToOptions(newAttributes)
	const existingSeries = options.series.find((series) => series.name === newAttributes.name)
	if (existingSeries) {
		Object.assign(existingSeries, optionsObject)
	} else {
		options.series.push(optionsObject)
	}
}
</script>
