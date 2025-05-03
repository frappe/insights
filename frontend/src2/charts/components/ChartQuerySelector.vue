<script setup lang="ts">
import { Table2 } from 'lucide-vue-next'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { wheneverChanges } from '../../helpers'
import useQuery from '../../query/query'
import { DropdownOption } from '../../types/query.types'

const query = defineModel<string>()
const props = defineProps<{ queries: DropdownOption[] }>()
if (!query.value && props.queries.length) {
	query.value = props.queries[0].value
}

wheneverChanges(
	query,
	() => {
		if (query.value) {
			const q = useQuery(query.value)
			if (q && !q.result.executedSQL) {
				q.execute()
			}
		}
	},
	{ immediate: true }
)
</script>

<template>
	<InlineFormControlLabel label="Query">
		<Autocomplete
			:showFooter="true"
			:options="props.queries"
			:modelValue="query"
			@update:modelValue="query = $event?.value"
		>
			<template #prefix>
				<Table2 class="mr-1.5 h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</Autocomplete>
	</InlineFormControlLabel>
</template>
