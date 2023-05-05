<template>
	<div class="h-full w-full bg-white px-8 py-4">
		<List
			title="Data Sources"
			:actions="[
				{
					label: 'New Data Source',
					appearance: 'white',
					iconLeft: 'plus',
					handler: () => (new_dialog = true),
				},
			]"
			:columns="columns"
			:data="sources.list"
			:rowClick="({ name }) => router.push({ name: 'DataSource', params: { name } })"
		>
		</List>
	</div>

	<Dialog :options="{ title: 'New Data Source' }" v-model="new_dialog">
		<template #body-content>
			<AddDatabase @success="onNewDatasource" />
		</template>
	</Dialog>
</template>

<script setup lang="jsx">
import List from '@/components/List.vue'
import AddDatabase from '@/components/SetupWizard/AddDatabase.vue'
import useDataSources from '@/datasource/useDataSources'
import { updateDocumentTitle } from '@/utils'
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const new_dialog = ref(false)
const router = useRouter()
const sources = useDataSources()
sources.reload()

const StatusCell = (props) => (
	<Badge color={props.row.status == 'Inactive' ? 'yellow' : 'green'}>{props.row.status}</Badge>
)
const columns = [
	{ label: 'Title', key: 'title' },
	{ label: 'Status', key: 'status', cellComponent: StatusCell },
	{ label: 'Type', key: 'source_type' },
	{ label: 'Created', key: 'created_from_now' },
]

const onNewDatasource = () => {
	new_dialog.value = false
	sources.reload()
}

const pageMeta = ref({
	title: 'Data Sources',
})
updateDocumentTitle(pageMeta)
</script>
