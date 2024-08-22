<script setup lang="ts">
import { Table2 } from 'lucide-vue-next'
import { WorkbookQuery } from '../../types/workbook.types'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'

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
		>
			<template #prefix>
				<Table2 class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</Autocomplete>
	</InlineFormControlLabel>
</template>
