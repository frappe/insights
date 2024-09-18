<script setup lang="tsx">
import { Avatar, Breadcrumbs, ListView } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import CSVIcon from '../components/Icons/CSVIcon.vue'
import DuckDBIcon from '../components/Icons/DuckDBIcon.vue'
import IndicatorIcon from '../components/Icons/IndicatorIcon.vue'
import MariaDBIcon from '../components/Icons/MariaDBIcon.vue'
import PostgreSQLIcon from '../components/Icons/PostgreSQLIcon.vue'
import SQLiteIcon from '../components/Icons/SQLiteIcon.vue'
import SelectTypeDialog from '../components/SelectTypeDialog.vue'
import useUserStore from '../users/users'
import ConnectMariaDBDialog from './ConnectMariaDBDialog.vue'
import ConnectPostgreSQLDialog from './ConnectPostgreSQLDialog.vue'
import useDataSourceStore from './data_source'
import { DataSourceListItem } from './data_source.types'
import UploadCSVFileDialog from './UploadCSVFileDialog.vue'

const dataSourceStore = useDataSourceStore()
dataSourceStore.getSources()

const searchQuery = ref('')
const filteredDataSources = computed(() => {
	if (!searchQuery.value) {
		return dataSourceStore.sources
	}
	return dataSourceStore.sources.filter((data_source) =>
		data_source.title.toLowerCase().includes(searchQuery.value.toLowerCase())
	)
})

const showNewSourceDialog = ref(false)
const showNewMariaDBDialog = ref(false)
const showNewPostgreSQLDialog = ref(false)
const showCSVFileUploadDialog = ref(false)

const sourceTypes = [
	{
		label: 'MariaDB',
		icon: <MariaDBIcon class="h-8 w-8" />,
		description: 'Connect to MariaDB database',
		onClick: () => {
			showNewSourceDialog.value = false
			showNewMariaDBDialog.value = true
		},
	},
	{
		label: 'PostgreSQL',
		icon: <PostgreSQLIcon class="h-8 w-8" />,
		description: 'Connect to PostgreSQL database',
		onClick: () => {
			showNewSourceDialog.value = false
			showNewPostgreSQLDialog.value = true
		},
	},
	{
		label: 'Upload CSV',
		icon: <CSVIcon class="h-8 w-8" />,
		description: 'Upload a CSV file',
		onClick: () => {
			showNewSourceDialog.value = false
			showCSVFileUploadDialog.value = true
		},
	},
]

const userStore = useUserStore()
const listOptions = ref({
	columns: [
		{
			label: 'Title',
			key: 'title',
			prefix: (props: any) => {
				const data_source = props.row as DataSourceListItem
				if (data_source.database_type === 'MariaDB') {
					return <MariaDBIcon class="h-5 w-5" />
				}
				if (data_source.database_type === 'PostgreSQL') {
					return <PostgreSQLIcon class="h-5 w-5" />
				}
				if (data_source.database_type === 'SQLite') {
					return <SQLiteIcon class="h-5 w-5" />
				}
				if (data_source.database_type === 'DuckDB') {
					return <DuckDBIcon class="h-5 w-5" />
				}
			},
		},
		{
			label: 'Status',
			key: 'status',
			prefix: (props: any) => {
				const color = props.row.status == 'Inactive' ? 'text-gray-500' : 'text-green-500'
				return <IndicatorIcon class={color} />
			},
		},
		{
			label: 'Owner',
			key: 'owner',
			prefix: (props: any) => {
				const data_source = props.row as DataSourceListItem
				const imageUrl = userStore.getUser(data_source.owner)?.user_image
				return <Avatar size="md" label={data_source.owner} image={imageUrl} />
			},
		},
		{ label: 'Created', key: 'created_from_now' },
		{ label: 'Modified', key: 'modified_from_now' },
	],
	rows: filteredDataSources,
	rowKey: 'name',
	options: {
		showTooltip: false,
		getRowRoute: (data_source: DataSourceListItem) => ({
			path: `/data-source/${data_source.name}`,
		}),
		emptyState: {
			title: 'No data sources.',
			description: 'No data sources to display.',
			button: {
				label: 'New Data Source',
				variant: 'solid',
				onClick: () => (showNewSourceDialog.value = true),
			},
		},
	},
})

document.title = 'Data Sources | Insights'
</script>

<template>
	<header class="mb-2 flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: 'Data Sources', route: '/data-source' }]" />
		<div class="flex items-center gap-2">
			<Button label="New Data Source" variant="solid" @click="showNewSourceDialog = true">
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
		<ListView class="h-full" v-bind="listOptions"> </ListView>
	</div>

	<SelectTypeDialog
		v-model="showNewSourceDialog"
		:types="sourceTypes"
		title="Select a data source"
	/>

	<ConnectMariaDBDialog v-model="showNewMariaDBDialog" />
	<ConnectPostgreSQLDialog v-model="showNewPostgreSQLDialog" />
	<UploadCSVFileDialog v-model="showCSVFileUploadDialog" />
</template>
