<template></template>

<script setup>
import { inject, computed, useAttrs } from 'vue'

const options = inject('options')
const subtext = computed(() => options.title?.subtext)
const SUBTEXT_HEIGHT = 20

const { top = 50, bottom = 50, left = 50, right = 50 } = useAttrs()

options.grid = {
	top: subtext.value ? top + SUBTEXT_HEIGHT : top,
	bottom: subtext.value ? bottom + SUBTEXT_HEIGHT : bottom,
	left: left,
	right: right,
}
</script>
