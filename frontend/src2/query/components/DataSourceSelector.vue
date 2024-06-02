<script setup>
import useDataSourceStore from '@/stores/dataSourceStore'
import { ChevronDown, Database, ListFilter } from 'lucide-vue-next'
import { computed } from 'vue'

const currentSourceName = defineModel()
const props = defineProps({
	placeholder: {
		type: String,
		default: 'Data source',
	},
})

const sources = useDataSourceStore()
const currentSource = computed(() => {
	return sources.list.find((source) => source.name === currentSourceName.value)
})
const dataSourceOptions = computed(() => {
	return sources.list.map((source) => ({
		label: source.title,
		value: source.name,
	}))
})
</script>

<template>
	<Autocomplete
		:options="dataSourceOptions"
		:modelValue="currentSourceName"
		@update:modelValue="currentSourceName = $event.value"
	>
		<template #target="{ togglePopover }">
			<Button variant="outline" @click="togglePopover">
				<template #prefix>
					<ListFilter class="h-4 w-4 flex-shrink-0" stroke-width="1.5" />
				</template>
				<span class="flex-1 truncate">
					{{ currentSource?.title || placeholder }}
				</span>
				<template #suffix>
					<ChevronDown class="h-4 w-4 flex-shrink-0" stroke-width="1.5" />
				</template>
			</Button>
		</template>
	</Autocomplete>
</template>
