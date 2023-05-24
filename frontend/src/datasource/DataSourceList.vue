<template>
	<div class="h-full w-full bg-white px-6 py-4">
		<Breadcrumbs :items="[{ label: 'Data Sources', href: '/data-source' }]"></Breadcrumbs>
		<ListView
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
		</ListView>
	</div>

	<NewDialogWithTypes
		v-model:show="new_dialog"
		title="Select Database Type"
		:types="databaseTypes"
	/>

	<ConnectMariaDBDialog v-model:show="showConnectMariaDBDialog" />
	<UploadSQLiteFileDialog v-model:show="showSQLiteFileUploadDialog" />
</template>

<script setup lang="jsx">
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ListView from '@/components/ListView.vue'
import useDataSources from '@/datasource/useDataSources'
import { updateDocumentTitle } from '@/utils'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import NewDialogWithTypes from '@/query/NewDialogWithTypes.vue'
import ConnectMariaDBDialog from '@/datasource/ConnectMariaDBDialog.vue'
import UploadSQLiteFileDialog from '@/datasource/UploadSQLiteFileDialog.vue'

const new_dialog = ref(false)
const sources = useDataSources()
sources.reload()

const StatusCell = (props) => (
	<Badge color={props.row.status == 'Inactive' ? 'yellow' : 'green'}>{props.row.status}</Badge>
)
const columns = [
	{ label: 'Title', key: 'title' },
	{ label: 'Status', key: 'status', cellComponent: StatusCell },
	{ label: 'Database Type', key: 'database_type' },
	{ label: 'Created', key: 'created_from_now' },
]

const router = useRouter()
const showConnectMariaDBDialog = ref(false)
const showSQLiteFileUploadDialog = ref(false)
const databaseTypes = ref([
	{
		label: 'MariaDB',
		description: 'Connect to a MariaDB database',
		icon: 'database',
		handler: () => {
			new_dialog.value = false
			showConnectMariaDBDialog.value = true
		},
	},
	{
		label: 'SQLite',
		description: 'Create or Upload a SQLite database',
		icon: 'database',
		tag: 'beta',
		handler: () => {
			new_dialog.value = false
			showSQLiteFileUploadDialog.value = true
		},
	},
])

const pageMeta = ref({ title: 'Data Sources' })
updateDocumentTitle(pageMeta)
</script>
