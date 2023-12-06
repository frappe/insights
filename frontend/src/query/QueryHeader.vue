<script setup lang="jsx">
import ContentEditable from '@/components/ContentEditable.vue'
import useDataSourceStore from '@/stores/dataSourceStore'
import { watchDebounced } from '@vueuse/core'
import { Component as ComponentIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import QueryMenu from './QueryMenu.vue'

const $notify = inject('$notify')
const query = inject('query')

const title = ref(query.doc.title)
watchDebounced(title, query.updateTitle, { debounce: 500 })
const sources = useDataSourceStore()

const SourceOption = (props) => {
	return (
		<div
			class="group flex w-full cursor-pointer items-center justify-between rounded-md px-2 py-2 text-sm hover:bg-gray-100"
			onClick={() => changeDataSource(props.name)}
		>
			<span>{props.label}</span>
			<FeatherIcon v-show={props.active} name="check" class="h-4 w-4 text-gray-600" />
		</div>
	)
}
const currentSource = computed(() => {
	return sources.list.find((source) => source.name === query.doc.data_source)
})
const dataSourceOptions = computed(() => {
	return sources.list.map((source) => ({
		component: (props) => (
			<SourceOption
				name={source.name}
				label={source.title}
				active={source.name === query.doc.data_source}
			/>
		),
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
	<div class="flex w-full items-center justify-between gap-4">
		<div class="flex items-center">
			<div v-if="query.doc.is_stored" class="mr-2">
				<ComponentIcon class="h-4 w-4 text-gray-600" fill="currentColor" />
			</div>
			<ContentEditable
				v-model="title"
				placeholder="Untitled Query"
				class="mr-3 rounded-sm text-xl font-medium !text-gray-900 focus:ring-2 focus:ring-gray-700 focus:ring-offset-4"
			></ContentEditable>
			<Dropdown
				class="mr-2"
				:button="{
					iconLeft: 'database',
					variant: 'outline',
					label: currentSource?.title || 'Select data source',
				}"
				:options="dataSourceOptions"
			/>
			<Button
				v-if="!query.doc.is_native_query"
				class="mr-2"
				variant="outline"
				icon="play"
				@click="query.execute()"
				:disabled="!query.doc.data_source"
				:loading="query.executing"
			/>
			<QueryMenu />
		</div>
		<div>
			<slot name="right-actions"></slot>
		</div>
	</div>
</template>
