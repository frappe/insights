<script setup lang="ts">
const query = defineModel()
const props = defineProps<{ queries: string[] }>()
</script>

<template>
	<div class="flex flex-col p-3">
		<Autocomplete
			label="Query"
			:showFooter="true"
			:options="props.queries"
			:modelValue="query"
			@update:modelValue="query = $event?.value"
		/>
	</div>
</template>
