<template></template>

<script setup>
import { inject, useAttrs } from 'vue'

const options = inject('options')

const { type = 'plain', ...attributes } = useAttrs()

options.legend = {
	type: type,
	icon: 'circle',
	pageIconSize: 12,
	pageIconColor: '#64748B',
	pageIconInactiveColor: '#C0CCDA',
	pageFormatter: '{current}',
	pageButtonItemGap: 2,
	...attributes,
}
</script>
