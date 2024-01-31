<script setup>
import useDataSourceStore from '@/stores/dataSourceStore'
import { ChevronDown, Database } from 'lucide-vue-next'
import { computed, inject } from 'vue'

const $notify = inject('$notify')
const query = inject('query')

const sources = useDataSourceStore()

const currentSource = computed(() => {
	return sources.list.find((source) => source.name === query.doc.data_source)
})
const dataSourceOptions = computed(() => {
	return sources.list.map((source) => ({
		label: source.title,
		value: source.name,
	}))
})

function changeDataSource(sourceName) {
	query.changeDataSource(sourceName).then(() => {
		$notify({
			title: 'Data source updated',
			variant: 'success',
		})
	})
}
</script>

<template>
	<Autocomplete
		:options="dataSourceOptions"
		:modelValue="query.doc.data_source"
		@update:modelValue="changeDataSource($event.value)"
	>
		<template #target="{ togglePopover }">
			<Button variant="outline" @click="togglePopover">
				<div class="flex items-center gap-2">
					<Database class="h-4 w-4 text-gray-600" />
					<span class="truncate">
						{{ currentSource?.title || 'Select data source' }}
					</span>
					<ChevronDown class="h-4 w-4 text-gray-600" />
				</div>
			</Button>
		</template>
	</Autocomplete>
</template>
