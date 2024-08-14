<script setup lang="tsx">
import { Avatar, ListView, Breadcrumbs } from 'frappe-ui'
import { PlusIcon, SearchIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import PostgresIcon from '../components/Icons/PostgresIcon.vue'
import useUserStore from '../users'
import useDataSourceStore, { DataSourceListItem } from './data_source'
import MariaDBIcon from '../components/Icons/MariaDBIcon.vue'
import SQLiteIcon from '../components/Icons/SQLiteIcon.vue'
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'

const router = useRouter()
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
					return <PostgresIcon class="h-5 w-5" />
				}
				if (data_source.database_type === 'SQLite') {
					return <SQLiteIcon class="h-5 w-5" />
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
			path: `/data_sources/${data_source.name}`,
		}),
		emptyState: {
			title: 'No data sources.',
			description: 'No data sources to display.',
			button: {
				label: 'New Data Source',
				variant: 'solid',
				onClick: () => {},
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
			<Button label="New Data Source" variant="solid" @click="">
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
</template>
