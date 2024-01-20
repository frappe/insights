<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs class="h-7" :items="[{ label: 'Data Sources' }]" />
		<div>
			<Button label="New Data Source" variant="solid" @click="new_dialog = true">
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>
	<ListView
		:columns="[
			{ label: 'Title', name: 'title' },
			{ label: 'Status', name: 'status' },
			{ label: 'Database Type', name: 'database_type' },
			{ label: 'Created', name: 'created_from_now' },
		]"
		:rows="sources.list"
	>
		<template #list-row="{ row: dataSource }">
			<ListRow
				as="router-link"
				:row="dataSource"
				:to="{
					name: 'DataSource',
					params: { name: dataSource.name },
				}"
			>
				<ListRowItem> {{ dataSource.title }} </ListRowItem>
				<ListRowItem class="space-x-2">
					<IndicatorIcon
						:class="
							dataSource.status == 'Inactive' ? 'text-gray-500' : 'text-green-500'
						"
					/>
					<span> {{ dataSource.status }} </span>
				</ListRowItem>
				<ListRowItem> {{ dataSource.database_type }} </ListRowItem>
				<ListRowItem> {{ dataSource.created_from_now }} </ListRowItem>
			</ListRow>
		</template>

		<template #emptyState>
			<div class="text-xl font-medium">No data sources.</div>
			<div class="mt-1 text-base text-gray-600">No data sources to display.</div>
			<Button
				class="mt-4"
				label="New Data Source"
				variant="solid"
				@click="new_dialog = true"
			/>
		</template>
	</ListView>

	<NewDialogWithTypes
		v-model:show="new_dialog"
		title="Select Source Type"
		:types="databaseTypes"
	/>

	<ConnectMariaDBDialog v-model:show="showConnectMariaDBDialog" />
	<ConnectPostgreDBDialog v-model:show="showConnectPostgreDBDialog" />
	<UploadCSVFileDialog v-model:show="showCSVFileUploadDialog" />
</template>

<script setup lang="jsx">
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import ListView from '@/components/ListView.vue'
import NewDialogWithTypes from '@/components/NewDialogWithTypes.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import ConnectMariaDBDialog from '@/datasource/ConnectMariaDBDialog.vue'
import ConnectPostgreDBDialog from '@/datasource/ConnectPostgreDBDialog.vue'
import UploadCSVFileDialog from '@/datasource/UploadCSVFileDialog.vue'
import useDataSourceStore from '@/stores/dataSourceStore'
import { updateDocumentTitle } from '@/utils'
import { ListRow, ListRowItem } from 'frappe-ui'
import { PlusIcon } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const new_dialog = ref(false)

const route = useRoute()
if (route.hash == '#new') {
	new_dialog.value = true
}

const sources = useDataSourceStore()

const StatusCell = (props) => (
	<Badge theme={props.row.status == 'Inactive' ? 'orange' : 'green'}>{props.row.status}</Badge>
)
const columns = []

const router = useRouter()
const showConnectMariaDBDialog = ref(false)
const showConnectPostgreDBDialog = ref(false)
const showCSVFileUploadDialog = ref(false)
const databaseTypes = ref([
	{
		label: 'MariaDB',
		description: 'Connect to a MariaDB database',
		icon: 'database',
		onClick: () => {
			new_dialog.value = false
			showConnectMariaDBDialog.value = true
		},
	},
	{
		label: 'PostgreSQL',
		description: 'Connect to a PostgreSQL database',
		icon: 'database',
		onClick: () => {
			new_dialog.value = false
			showConnectPostgreDBDialog.value = true
		},
	},
	{
		label: 'CSV',
		description: 'Upload a CSV file',
		icon: 'file',
		onClick: () => {
			new_dialog.value = false
			showCSVFileUploadDialog.value = true
		},
	},
])

const pageMeta = ref({ title: 'Data Sources' })
updateDocumentTitle(pageMeta)
</script>
