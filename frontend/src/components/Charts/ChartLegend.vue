<template></template>

<script setup>
import { inject, useAttrs } from 'vue'

const options = inject('options')

const { type = 'plain', ...attributes } = useAttrs()

options.legend = {
	type: type,
	...attributes,
}
</script>
