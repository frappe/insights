<script setup lang="jsx">
import useDataSources from '@/datasource/useDataSources'
import EditableTitle from '@/query/EditableTitle.vue'
import QueryMenu from '@/query/QueryMenu.vue'
import { computed, inject } from 'vue'

const $notify = inject('$notify')
const query = inject('query')

const updateTitle = (title) => {
	if (!title || title === query.doc.title) return
	query.setValue.submit({ title }).then(() => {
		$notify({
			title: 'Query title updated',
			appearance: 'success',
		})
		query.doc.title = title
	})
}

const sources = useDataSources()
sources.reload()
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
			appearance: 'success',
		})
		query.doc.data_source = sourceName
	})
}
</script>

<template>
	<div class="mr-2 flex h-full items-center space-x-2">
		<EditableTitle :title="query.doc.title" @update="updateTitle" />
		<Dropdown
			:button="{
				iconLeft: 'database',
				appearance: 'minimal',
				label: query.doc.data_source || 'Select data source',
			}"
			:options="dataSourceOptions"
		/>
		<QueryMenu />
	</div>
</template>
