<script setup lang="tsx">
import { Avatar, Breadcrumbs } from 'frappe-ui'
import { ListView } from 'frappe-ui/experimental'
import { List, ListCell, ListRow } from 'frappe-ui/list'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import CSVIcon from '../components/Icons/CSVIcon.vue'
import IndicatorIcon from '../components/Icons/IndicatorIcon.vue'
import SelectTypeDialog from '../components/SelectTypeDialog.vue'
import { useIsMobile } from '../composables/useIsMobile'
import session from '../session'
import useUserStore from '../users/users'
import ConnectMariaDBDialog from './ConnectMariaDBDialog.vue'
import ConnectPostgreSQLDialog from './ConnectPostgreSQLDialog.vue'
import useDataSourceStore, { getDatabaseLogo } from './data_source'
import { DataSourceListItem } from './data_source.types'
import UploadCSVFileDialog from './UploadCSVFileDialog.vue'
import ConnectDuckDBDialog from './ConnectDuckDBDialog.vue'
import ConnectClickhouseDialog from './ConnectClickhouseDialog.vue'
import { __ } from '../translation'

const dataSourceStore = useDataSourceStore()
dataSourceStore.getSources()

const searchQuery = ref('')
const filteredDataSources = computed(() => {
	if (!searchQuery.value) {
		return dataSourceStore.sources
	}
	return dataSourceStore.sources.filter((data_source) =>
		data_source.title.toLowerCase().includes(searchQuery.value.toLowerCase()),
	)
})

// a phone lists them as the Dashboards and Workbooks lists do: two-line rows
const isMobile = useIsMobile()
function phoneMeta(data_source: DataSourceListItem) {
	return [
		data_source.database_type,
		data_source.status === 'Inactive' && __('Inactive'),
		data_source.modified_from_now,
	]
		.filter(Boolean)
		.join(' · ')
}

const canConnect = session.user.is_admin
const showNewSourceDialog = ref(false)
const showNewMariaDBDialog = ref(false)
const showNewPostgreSQLDialog = ref(false)
const showNewClickHouseDialog = ref(false)
const showNewDuckDBDialog = ref(false)
const showCSVFileUploadDialog = ref(false)

const sourceTypes = [
	{
		label: __('MariaDB'),
		icon: getDatabaseLogo('MariaDB'),
		description: __('Connect to MariaDB database'),
		onClick: () => {
			showNewSourceDialog.value = false
			showNewMariaDBDialog.value = true
		},
	},
	{
		label: __('PostgreSQL'),
		icon: getDatabaseLogo('PostgreSQL'),
		description: __('Connect to PostgreSQL database'),
		onClick: () => {
			showNewSourceDialog.value = false
			showNewPostgreSQLDialog.value = true
		},
	},
	{
		label: __('ClickHouse'),
		icon: getDatabaseLogo('ClickHouse'),
		description: __('Connect to ClickHouse database'),
		onClick: () => {
			showNewSourceDialog.value = false
			showNewClickHouseDialog.value = true
		},
	},
	{
		label: __('DuckDB'),
		icon: getDatabaseLogo('DuckDB'),
		description: __('Connect to DuckDB database'),
		onClick: () => {
			showNewSourceDialog.value = false
			showNewDuckDBDialog.value = true
		},
	},
	{
		label: __('Upload CSV or Excel'),
		icon: <CSVIcon class="h-8 w-8" />,
		description: __('Upload a CSV or Excel file to create a new data source'),
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
			label: __('Title'),
			key: 'title',
			prefix: (props: any) => {
				const data_source = props.row as DataSourceListItem
				return getDatabaseLogo(data_source.database_type, 'sm')
			},
		},
		{
			label: __('Status'),
			key: 'status',
			prefix: (props: any) => {
				const color =
					props.row.status == 'Inactive' ? 'text-ink-gray-4' : 'text-ink-green-5'
				return <IndicatorIcon class={color} />
			},
		},
		{
			label: __('Owner'),
			key: 'owner',
			getLabel(props: any) {
				const data_source = props.row as DataSourceListItem
				const user = userStore.getUser(data_source.owner)
				return user?.full_name || data_source.owner
			},
			prefix: (props: any) => {
				const data_source = props.row as DataSourceListItem
				const imageUrl = userStore.getUser(data_source.owner)?.user_image
				return <Avatar size="md" label={data_source.owner} image={imageUrl} />
			},
		},
		{ label: __('Created'), key: 'created_from_now' },
		{ label: __('Modified'), key: 'modified_from_now' },
	],
	rows: filteredDataSources,
	rowKey: 'name',
	options: {
		showTooltip: false,
		getRowRoute: (data_source: DataSourceListItem) => ({
			path: `/data-source/${data_source.name}`,
		}),
		emptyState: {
			title: __('No data sources.'),
			description: __('No data sources to display.'),
			button: canConnect
				? {
						label: __('New Data Source'),
						variant: 'solid',
						onClick: () => (showNewSourceDialog.value = true),
				  }
				: undefined,
		},
	},
})

document.title = __('Data Sources | Insights')
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: __('Data Sources'), route: '/data-source' }]" />
		<div class="flex items-center gap-2">
			<Button
				v-if="canConnect"
				:label="__('New Data Source')"
				variant="solid"
				@click="showNewSourceDialog = true"
			>
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl
				class="max-sm:flex-1"
				:placeholder="__('Search by Title')"
				v-model="searchQuery"
				:debounce="300"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-ink-gray-4" />
				</template>
			</FormControl>
		</div>
		<List
			v-if="isMobile && filteredDataSources.length"
			class="-mx-3 list-row-px-3"
			:columns="['2rem', 'minmax(0,1fr)']"
			:row-height="56"
		>
			<ListRow
				v-for="data_source in filteredDataSources"
				:key="data_source.name"
				class="active:bg-surface-gray-2"
			>
				<ListCell>
					<RouterLink
						:to="`/data-source/${data_source.name}`"
						class="absolute inset-0"
						:aria-label="data_source.title"
					/>
					<component :is="getDatabaseLogo(data_source.database_type, 'sm')" />
				</ListCell>
				<ListCell class="flex-col !items-start justify-center">
					<span class="w-full truncate text-base text-ink-gray-8">
						{{ data_source.title }}
					</span>
					<span class="w-full truncate text-sm text-ink-gray-5">
						{{ phoneMeta(data_source) }}
					</span>
				</ListCell>
			</ListRow>
		</List>
		<div
			v-else-if="isMobile && !dataSourceStore.loading"
			class="flex flex-1 flex-col items-center justify-center text-base"
		>
			<div class="text-lg-medium">
				{{ searchQuery ? __('No data sources found') : __('No data sources.') }}
			</div>
			<div class="mt-1 text-ink-gray-5">
				{{ searchQuery ? __('Try a different title.') : __('No data sources to display.') }}
			</div>
		</div>
		<ListView v-else-if="!isMobile" class="h-full" v-bind="listOptions"> </ListView>
	</div>

	<SelectTypeDialog
		v-model="showNewSourceDialog"
		:types="sourceTypes"
		:title="__('Select a data source')"
	/>

	<ConnectMariaDBDialog v-model="showNewMariaDBDialog" />
	<ConnectPostgreSQLDialog v-model="showNewPostgreSQLDialog" />
	<ConnectClickhouseDialog v-model="showNewClickHouseDialog" />
	<ConnectDuckDBDialog v-model="showNewDuckDBDialog" />
	<UploadCSVFileDialog v-model="showCSVFileUploadDialog" />
</template>
