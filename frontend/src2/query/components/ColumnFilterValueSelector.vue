<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { CheckSquare, SearchIcon, Square } from 'lucide-vue-next'
import { ref } from 'vue'
import { QueryResultColumn } from '../../types/query.types'

const props = defineProps<{
	column: QueryResultColumn
	valuesProvider: (search: string) => Promise<string[]>
}>()
const selectedValues = defineModel<any[]>({
	type: Array,
	default: () => [],
})

const distinctColumnValues = ref<any[]>([])
const searchInput = ref('')
const fetchingValues = ref(false)
watchDebounced(
	() => searchInput.value,
	(value) => {
		fetchingValues.value = true
		// query
		// 	.getDistinctColumnValues(props.column.name, value)
		props
			.valuesProvider(value)
			.then((values: string[]) => (distinctColumnValues.value = values))
			.finally(() => (fetchingValues.value = false))
	},
	{ debounce: 300, immediate: true }
)

function toggleValue(value: string) {
	if (selectedValues.value.includes(value)) {
		selectedValues.value = selectedValues.value.filter((v) => v !== value)
	} else {
		selectedValues.value = [...selectedValues.value, value]
	}
}
</script>

<template>
	<div
		v-if="fetchingValues"
		class="flex items-center justify-center gap-2 p-2 text-base text-gray-600"
	>
		<LoadingIndicator class="h-4 w-4 text-gray-600" />
		<span>Loading values...</span>
	</div>
	<div v-else class="flex flex-col gap-2">
		<FormControl placeholder="Search" v-model="searchInput">
			<template #prefix>
				<SearchIcon class="h-4 w-4 text-gray-400" />
			</template>
		</FormControl>
		<div class="max-h-[10rem] overflow-y-scroll">
			<div
				v-for="(value, idx) in distinctColumnValues.slice(0, 50)"
				:key="value || idx"
				class="flex cursor-pointer items-center justify-between gap-2 rounded px-1 py-1.5 text-base hover:bg-gray-100"
				@click.prevent.stop="toggleValue(value)"
			>
				<component
					:is="selectedValues.includes(value) ? CheckSquare : Square"
					class="h-4 w-4 text-gray-600"
				/>
				<span class="flex-1 truncate"> {{ value }} </span>
			</div>
		</div>
	</div>
</template>
