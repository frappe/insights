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

	<div class="mb-4 flex h-full flex-col gap-2 overflow-auto px-4">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search by Title" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>
		<ListView
			:columns="dataSourceListColumns"
			:rows="filteredSourceList"
			:row-key="'name'"
			:options="{
				showTooltip: false,
				getRowRoute: (dataSource) => ({
					name: 'DataSource',
					params: { name: dataSource.name },
				}),
				emptyState: {
					title: 'No Data Sources.',
					description: 'No data sources to display.',
					button: {
						label: 'New Data Source',
						variant: 'solid',
						onClick: () => (new_dialog = true),
					},
				},
			}"
		>
		</ListView>
	</div>

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
import NewDialogWithTypes from '@/components/NewDialogWithTypes.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import ConnectMariaDBDialog from '@/datasource/ConnectMariaDBDialog.vue'
import ConnectPostgreDBDialog from '@/datasource/ConnectPostgreDBDialog.vue'
import UploadCSVFileDialog from '@/datasource/UploadCSVFileDialog.vue'
import useDataSourceStore from '@/stores/dataSourceStore'
import { updateDocumentTitle } from '@/utils'
import { ListView } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const new_dialog = ref(false)

const route = useRoute()
if (route.hash == '#new') {
	new_dialog.value = true
}

const sources = useDataSourceStore()
const searchQuery = ref('')
const filteredSourceList = computed(() => {
	if (searchQuery.value) {
		return sources.list.filter((source) => {
			return source.title.toLowerCase().includes(searchQuery.value.toLowerCase())
		})
	}
	return sources.list
})

const router = useRouter()
const showConnectMariaDBDialog = ref(false)
const showConnectPostgreDBDialog = ref(false)
const showCSVFileUploadDialog = ref(false)
const databaseTypes = ref([
	{
		label: 'MariaDB',
		description: 'Connect to a MariaDB database',
		imgSrc: '/src/assets/MariaDBIcon.png',
		onClick: () => {
			new_dialog.value = false
			showConnectMariaDBDialog.value = true
		},
	},
	{
		label: 'PostgreSQL',
		description: 'Connect to a PostgreSQL database',
		imgSrc: '/src/assets/PostgreSQLIcon.png',
		onClick: () => {
			new_dialog.value = false
			showConnectPostgreDBDialog.value = true
		},
	},
	{
		label: 'CSV',
		description: 'Upload a CSV file',
		imgSrc: '/src/assets/SheetIcon.png',
		onClick: () => {
			new_dialog.value = false
			showCSVFileUploadDialog.value = true
		},
	},
])

const dataSourceListColumns = [
	{ label: 'Title', key: 'title' },
	{
		label: 'Status',
		key: 'status',
		prefix: ({ row }) => {
			const color = row.status == 'Inactive' ? 'text-gray-500' : 'text-green-500'
			return <IndicatorIcon class={color} />
		},
	},
	{ label: 'Database Type', key: 'database_type' },
	{ label: 'Created', key: 'created_from_now' },
]

const pageMeta = ref({ title: 'Data Sources' })
updateDocumentTitle(pageMeta)
</script>
