<script setup>
import useDataSourceStore from '@/stores/dataSourceStore'
import { ChevronDown, Database } from 'lucide-vue-next'
import { computed } from 'vue'

const currentSourceName = defineModel()
const props = defineProps({
	placeholder: {
		type: String,
		default: 'Select data source',
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
				<div class="flex max-w-[12rem] items-center gap-2">
					<Database class="h-4 w-4 flex-shrink-0 text-gray-600" />
					<span class="flex-1 truncate">
						{{ currentSource?.title || placeholder }}
					</span>
					<ChevronDown class="h-4 w-4 flex-shrink-0 text-gray-600" />
				</div>
			</Button>
		</template>
	</Autocomplete>
</template>
