<script setup lang="ts">
import { FormControl } from 'frappe-ui'
</script>

<template>
	<FormControl v-bind="$attrs" autocomplete="off">
		<slot></slot>
	</FormControl>
</template>
