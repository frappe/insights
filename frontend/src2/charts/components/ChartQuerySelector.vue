<script setup lang="ts">
import { Table2 } from 'lucide-vue-next'
import { computed } from 'vue'
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
			useQuery(query.value)?.ensureResult()
		}
	},
	{ immediate: true },
)

// the query's own pane is not on screen, so a failed run is told here or nowhere
const failure = computed(() => (query.value ? useQuery(query.value)?.executionError : ''))
</script>

<template>
	<InlineFormControlLabel :label="__('Query')">
		<Combobox
			class="w-full"
			:options="props.queries"
			:modelValue="query"
			@update:modelValue="query = $event"
		>
			<template #prefix>
				<Table2 class="mr-1.5 h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
			</template>
		</Combobox>
	</InlineFormControlLabel>
	<p v-if="failure" class="whitespace-pre-wrap font-mono text-xs leading-5 text-ink-red-4">
		{{ failure }}
	</p>
</template>
