<script setup lang="ts">
import { Table2 } from 'lucide-vue-next'
import { WorkbookQuery } from '../../types/workbook.types'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { wheneverChanges } from '../../helpers'
import { getCachedQuery } from '../../query/query'

const query = defineModel()
const props = defineProps<{ queries: WorkbookQuery[] }>()
if (!query.value && props.queries.length) {
	query.value = props.queries[0].name
}

wheneverChanges(query, (value: string) => {
	if (value) {
		const q = getCachedQuery(value)
		if (q && !q.result.executedSQL) {
			q.execute()
		}
	}
})
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
