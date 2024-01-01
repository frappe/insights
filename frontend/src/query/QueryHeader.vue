<script setup lang="jsx">
import useDataSourceStore from '@/stores/dataSourceStore'
import { watchDebounced } from '@vueuse/core'
import { ChevronDown, Database, Play } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import QueryMenu from './QueryMenu.vue'

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
	<div class="flex items-center gap-2">
		<QueryMenu></QueryMenu>
		<Autocomplete
			:options="dataSourceOptions"
			:modelValue="query.doc.data_source"
			@update:modelValue="changeDataSource($event.value)"
		>
			<template #target="{ togglePopover }">
				<Button
					:variant="currentSource?.title ? 'outline' : 'solid'"
					@click="togglePopover"
				>
					<div class="flex items-center gap-2">
						<Database class="h-4 w-4" />
						<span class="truncate">
							{{ currentSource?.title || 'Select data source' }}
						</span>
						<ChevronDown class="h-4 w-4" />
					</div>
				</Button>
			</template>
		</Autocomplete>

		<Button
			v-if="!query.doc.is_script_query && !query.doc.is_native_query"
			variant="solid"
			@click="query.execute()"
			:loading="query.executing"
			:disabled="!query.doc.data_source || !query.doc.sql"
		>
			<template #prefix>
				<Play class="h-4 w-4"></Play>
			</template>
			<span>Execute</span>
		</Button>
	</div>
</template>
