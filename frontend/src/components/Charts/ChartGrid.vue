<template>
	<slot v-bind="$attrs"></slot>
</template>

<script setup>
import { inject, useAttrs } from 'vue'
const options = inject('options')
const defaults = {
	top: 25,
	bottom: 35,
	left: 20,
	right: 30,
	containLabel: true,
}
options.grid = { ...defaults, ...useAttrs() }
</script>
