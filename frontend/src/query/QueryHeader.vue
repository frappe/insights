<script setup lang="jsx">
import useDataSourceStore from '@/stores/dataSourceStore'
import ContentEditable from '@/notebook/ContentEditable.vue'
import QueryMenu from '@/query/QueryMenu.vue'
import { debounce } from 'frappe-ui'
import { Component } from 'lucide-vue-next'
import { Bookmark } from 'lucide-vue-next'
import { computed, inject } from 'vue'

const $notify = inject('$notify')
const query = inject('query')

const debouncedUpdateTitle = debounce(async (title) => {
	await query.setValue.submit({ title })
	query.doc.title = title
}, 1500)

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
	query.updateDoc({ data_source: sourceName }).then(() => {
		$notify({
			title: 'Data source updated',
			variant: 'success',
		})
		query.doc.data_source = sourceName
	})
}
</script>

<template>
	<div class="mr-2 flex h-full items-center">
		<div v-if="query.doc.is_saved_as_table" class="mr-2">
			<Component class="h-4 w-4 text-gray-600" fill="currentColor" />
		</div>
		<ContentEditable
			class="mr-3 rounded-sm text-xl font-medium !text-gray-800 focus:ring-2 focus:ring-gray-700 focus:ring-offset-4"
			v-model="query.doc.title"
			@update:model-value="debouncedUpdateTitle"
			placeholder="Untitled Query"
		></ContentEditable>
		<Dropdown
			class="mr-2"
			v-if="!query.doc.is_assisted_query"
			:button="{
				iconLeft: 'database',
				variant: 'outline',
				label: currentSource?.title || 'Select data source',
			}"
			:options="dataSourceOptions"
		/>
		<QueryMenu />
	</div>
</template>
