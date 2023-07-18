<script setup lang="jsx">
import useDataSources from '@/datasource/useDataSources'
import QueryMenu from '@/query/QueryMenu.vue'
import { debounce } from 'frappe-ui'
import { computed, inject } from 'vue'
import ContentEditable from '@/notebook/ContentEditable.vue'

const $notify = inject('$notify')
const query = inject('query')

const debouncedUpdateTitle = debounce(async (title) => {
	await query.setValue.submit({ title })
	query.doc.title = title
}, 500)

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
			variant: 'success',
		})
		query.doc.data_source = sourceName
	})
}
</script>

<template>
	<div class="mr-2 flex h-full items-center space-x-3">
		<ContentEditable
			class="text-xl"
			v-model="query.doc.title"
			@update:model-value="debouncedUpdateTitle"
			placeholder="Untitled Query"
		></ContentEditable>
		<Dropdown
			:button="{
				iconLeft: 'database',
				variant: 'outline',
				label: query.doc.data_source || 'Select data source',
			}"
			:options="dataSourceOptions"
		/>
		<QueryMenu />
	</div>
</template>
