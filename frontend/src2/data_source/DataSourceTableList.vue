<script setup lang="tsx">
import { Breadcrumbs, ListView, Button, FormControl } from 'frappe-ui'
import { MoreHorizontal, RefreshCcw, SearchIcon } from 'lucide-vue-next'
import { h, ref, computed, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import useDataSourceStore from './data_source'
import useTableStore, { DataSourceTable } from './tables'
import { usePagination } from '../composables/usePagination'
import { useUrlPagination } from '../composables/useUrlPagination'
import DataTableFooter from '../components/DataTableFooter.vue'
import { __ } from '../translation'

const props = defineProps<{ name: string }>()

const route = useRoute()
const router = useRouter()
const dataSourceStore = useDataSourceStore()
const tableStore = useTableStore()
const dataSource = computed(() => dataSourceStore.getSource(props.name))

const listWrapper = ref<HTMLElement | null>(null)
const listView = ref<any>(null)

const {
	searchQuery,
	items: filteredTables,
	totalCount,
	currentPage,
	isLoading,
	isError,
	refresh,
} = useUrlPagination(
	(search, limit, offset) => tableStore.getTables(props.name, search, limit, offset),
	(search) => tableStore.getTablesCount(props.name, search),
	100,
	() => {
		if (listWrapper.value) {
			const scrollEl = listWrapper.value.querySelector('.overflow-y-auto')
			if (scrollEl) {
				scrollEl.scrollTop = 0
			}
		}
		if (listView.value?.selections) {
			listView.value.selections.clear()
		}
	},
)

const pagination = usePagination({
	rowCount: computed(() => filteredTables.value.length),
	totalRowCount: totalCount,
	pageSize: 100,
	currentPage: currentPage,
	onPageChange: (page) => {
		router.replace({ query: { ...route.query, page } })
	},
})

const listOptions = computed(() => ({
	columns: [
		{
			label: __('Table Name'),
			key: 'table_name',
		},
	],
	rows: filteredTables.value,
	rowKey: 'table_name',
	options: {
		showTooltip: false,
		getRowRoute: (table: DataSourceTable) => ({
			path: `/data-source/${props.name}/${table.table_name}`,
		}),
		emptyState: {
			title: __('No Tables Found'),
			description: __('No tables found for the selected data source.'),
			button: {
				label: __('Refresh'),
				iconLeft: 'refresh-ccw',
				variant: 'outline',
				loading: tableStore.updatingDataSourceTables,
				onClick: () => tableStore.updateDataSourceTables(props.name).then(refresh),
			},
		},
	},
}))

watchEffect(() => {
	document.title = `Tables | ${dataSource.value?.title || props.name}`
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs
			:items="[
				{ label: __('Data Sources'), route: '/data-source' },
				{ label: dataSource?.title || props.name, route: `/data-source/${props.name}` },
			]"
		/>
	</header>

	<div class="flex flex-1 flex-col overflow-hidden">
		<div class="flex gap-2 overflow-visible px-5 py-4">
			<FormControl
				:placeholder="__('Search by Table Name')"
				v-model="searchQuery"
				autocomplete="off"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
			<Dropdown
				:options="[
					{
						label: __('Update Tables'),
						onClick: () =>
							tableStore.updateDataSourceTables(props.name).then(() => refresh()),
						icon: () =>
							h(RefreshCcw, {
								class: 'h-4 w-4 text-gray-700',
								'stroke-width': '1.5',
							}),
					},
					dataSource?.is_frappe_db
						? {
								label: __('Update Table Links'),
								onClick: () => tableStore.updateTableLinks(props.name),
								icon: () =>
									h(RefreshCcw, {
										class: 'h-4 w-4 text-gray-700',
										'stroke-width': '1.5',
									}),
						  }
						: null,
				]"
			>
				<Button>
					<template #icon>
						<MoreHorizontal class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Dropdown>
		</div>
		<div class="flex flex-1 flex-col min-h-0 overflow-hidden px-5" ref="listWrapper">
			<ListView ref="listView" class="h-full" v-bind="listOptions"> </ListView>
		</div>
		<DataTableFooter
			:pagination="pagination"
			:total-row-count="totalCount ?? undefined"
			@prev="pagination.prev()"
			@next="pagination.next()"
		/>
	</div>
</template>
