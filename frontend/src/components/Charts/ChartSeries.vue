<template></template>

<script setup>
import { inject, useAttrs, watch } from 'vue'

const attributes = useAttrs()
const options = inject('options')
const convertAttributesToOptions = inject('convertAttributesToOptions')

watch(() => attributes, updateOptions, { deep: true, immediate: true })
function updateOptions(newAttributes) {
	const optionsObject = convertAttributesToOptions(newAttributes)
	options.series = [...(options.series || []), optionsObject]
}
</script>
