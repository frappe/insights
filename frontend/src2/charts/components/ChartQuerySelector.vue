<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { WorkbookQuery } from '../../types/workbook.types'

const query = defineModel()
const props = defineProps<{ queries: WorkbookQuery[] }>()
if (!query.value && props.queries.length === 1) {
	query.value = props.queries[0].name
}
</script>

<template>
	<InlineFormControlLabel label="Query">
		<Autocomplete
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
	</InlineFormControlLabel>
</template>
