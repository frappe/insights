<script setup lang="ts">
import { WorkbookQuery } from '../../types/workbook.types'

const query = defineModel()
const props = defineProps<{ queries: WorkbookQuery[] }>()
</script>

<template>
	<div class="flex flex-col p-3">
		<Autocomplete
			label="Query"
			:showFooter="true"
			:options="
				props.queries.map((q) => {
					return {
						label: q.title,
						value: q.name,
					}
				})
			"
			:modelValue="query"
			@update:modelValue="query = $event?.value"
		/>
	</div>
</template>
