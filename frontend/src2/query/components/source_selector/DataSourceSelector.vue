<script setup>
import { ChevronDown, Database, ListFilter } from 'lucide-vue-next'
import { computed } from 'vue'
import useDataSourceStore from '../../../data_source/data_source'
import useSettings from '../../../settings/settings'

const currentSourceName = defineModel()
const props = defineProps({
	placeholder: {
		type: String,
		default: 'Data source',
	},
})

const dataSourceStore = useDataSourceStore()
const settings = useSettings()

const currentSource = computed(() => {
	if (currentSourceName.value === 'warehouse_tables') {
		return { name: 'warehouse_tables', title: 'Warehouse Tables' }
	}
	return dataSourceStore.sources.find((source) => source.name === currentSourceName.value)
})

const dataSourceOptions = computed(() => {
	const options = dataSourceStore.sources.map((source) => ({
		label: source.title,
		value: source.name,
	}))

	if (settings.doc.enable_data_store) {
		options.push({
			label: 'Warehouse Tables',
			value: 'warehouse_tables',
		})
	}

	return options
})
</script>

<template>
	<Autocomplete
		:options="dataSourceOptions"
		:modelValue="currentSourceName"
		@update:modelValue="currentSourceName = $event?.value || ''"
	>
		<template #target="{ togglePopover }">
			<Button variant="outline" @click="togglePopover">
				<template #prefix>
					<Database class="h-3.5 w-3.5 flex-shrink-0" stroke-width="1.5" />
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
