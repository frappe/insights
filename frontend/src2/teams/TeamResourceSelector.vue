<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { call } from 'frappe-ui'
import { ChevronDown, ChevronRight, SearchIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import useDataSourceStore from '../data_source/data_source'
import { DataSourceListItem } from '../data_source/data_source.types'
import useTableStore, { DataSourceTable } from '../data_source/tables'
import { toOptions, wheneverChanges } from '../helpers'
import ExpressionEditor from '../query/components/ExpressionEditor.vue'
import { TeamPermission } from './teams'

const teamPermissions = defineModel<TeamPermission[]>({
	required: true,
})

const dataSourceStore = useDataSourceStore()
const tableStore = useTableStore()

const selectedDataSources = ref<string[]>([])
const selectedTables = ref<Record<string, string[]>>({})
const tableRestrictions = ref<Record<string, string>>({})

if (teamPermissions.value.length) {
	selectedDataSources.value = teamPermissions.value
		.filter((p) => p.type === 'Source')
		.map((p) => p.resource_name)

	for (const ds of selectedDataSources.value) {
		selectDataSource(ds, true)
	}

	const permittedTableNames = teamPermissions.value
		.filter((p) => p.type === 'Table')
		.map((p) => p.resource_name)

	if (permittedTableNames.length) {
		const tablesBySource: Record<string, string[]> = await call(
			'insights.api.data_sources.get_data_sources_of_tables',
			{ table_names: permittedTableNames }
		)
		selectedTables.value = tablesBySource
		setTimeout(() => {
			// wrap in setTimeout to avoid 'referenced before assignment' error
			for (const data_source of Object.keys(tablesBySource)) {
				if (!dataSourceTables.value[data_source]?.length) {
					fetchTables(data_source)
				}
			}
		}, 0)

		for (const table of permittedTableNames) {
			const tablePerm = teamPermissions.value.find((p) => p.resource_name === table)
			const tableRestriction = tablePerm?.table_restrictions
			if (tableRestriction) {
				tableRestrictions.value[table] = tableRestriction
			}
		}
	}
}

watchDebounced(
	() => [selectedDataSources.value, selectedTables.value, tableRestrictions.value],
	() => {
		const dataSourcesPerms: TeamPermission[] = selectedDataSources.value.map((ds) => {
			return {
				type: 'Source',
				resource_type: 'Insights Data Source v3',
				resource_name: ds,
			}
		})
		const tablePerms: TeamPermission[] = Object.entries(selectedTables.value).flatMap(
			([ds, tables]) => {
				return tables.map((table) => {
					return {
						type: 'Table',
						resource_type: 'Insights Table v3',
						resource_name: table,
						table_restrictions: tableRestrictions.value[table] || '',
					}
				})
			}
		)
		const newPermissions = [...dataSourcesPerms, ...tablePerms]
		const hasResourcesChanged =
			JSON.stringify(
				newPermissions
					.map((p) => p.resource_name)
					.filter(Boolean)
					.sort()
			) !==
			JSON.stringify(
				teamPermissions.value
					.map((p) => p.resource_name)
					.filter(Boolean)
					.sort()
			)

		const hasRestrictionsChanged =
			JSON.stringify(
				newPermissions
					.map((p) => p.table_restrictions)
					.filter(Boolean)
					.sort()
			) !==
			JSON.stringify(
				teamPermissions.value
					.map((p) => p.table_restrictions)
					.filter(Boolean)
					.sort()
			)

		if (hasResourcesChanged || hasRestrictionsChanged) {
			teamPermissions.value = newPermissions
		}
	},
	{ debounce: 300, deep: true }
)

const dataSources = ref<DataSourceListItem[]>([])
dataSourceStore.getSources().then((sources) => {
	dataSources.value = sources.sort((a, b) => a.title.localeCompare(b.title))
	selectedTables.value = dataSources.value.reduce((acc, ds) => {
		acc[ds.name] = acc[ds.name] || []
		return acc
	}, selectedTables.value)
})

const expandedDataSource = ref<string | null>(null)
const expandedDataSourceTables = computed(() => {
	if (!expandedDataSource.value) {
		return []
	}
	return dataSourceTables.value[expandedDataSource.value] || []
})

const tableSearchQuery = ref('')
const dataSourceTables = ref<Record<string, DataSourceTable[]>>({})
function toggleExpandedDataSource(dataSource: string) {
	if (expandedDataSource.value === dataSource) {
		expandedDataSource.value = null
	} else {
		expandedDataSource.value = dataSource
		fetchTables(dataSource)
	}
	const el = document.querySelector(`[data-source="${dataSource}"]`)
	if (el) {
		el.scrollIntoView({ behavior: 'smooth' })
	}
}
async function fetchTables(dataSource: string) {
	return tableStore.getTables(dataSource, '', 0).then((tables) => {
		Object.assign(dataSourceTables.value, {
			[dataSource]: tables,
		})
		return tables
	})
}

function isDataSourceSelected(dataSource: string) {
	return (
		selectedDataSources.value.some((ds) => ds === dataSource) ||
		selectedTables.value[dataSource]?.length === dataSourceTables.value[dataSource]?.length
	)
}
function isTableSelected(dataSource: string, table: string) {
	return selectedTables.value[dataSource]?.some((t) => t === table)
}
function selectDataSource(dataSource: string, selected: boolean) {
	if (selected) {
		selectedDataSources.value.push(dataSource)
		if (expandedDataSource.value === dataSource && expandedDataSourceTables.value) {
			selectedTables.value[dataSource] = expandedDataSourceTables.value.map((t) => t.name)
		} else {
			fetchTables(dataSource).then((tables) => {
				selectedTables.value[dataSource] = tables.map((t) => t.name)
			})
		}
	} else {
		selectedDataSources.value = selectedDataSources.value.filter((ds) => ds !== dataSource)
		selectedTables.value[dataSource] = []
	}
}
function selectTable(dataSource: string, table: string, selected: boolean) {
	if (!expandedDataSource.value) {
		return
	}
	if (isDataSourceSelected(dataSource)) {
		selectedDataSources.value = selectedDataSources.value.filter((ds) => ds !== dataSource)
	}
	if (selected) {
		selectedTables.value[dataSource].push(table)
	} else {
		selectedTables.value[dataSource] = selectedTables.value[dataSource].filter(
			(t) => t !== table
		)
	}
}

const expandedTable = ref<string | null>(null)
const expandedTableColumns = ref<ColumnOption[]>([])
wheneverChanges(
	() => [expandedDataSource.value, expandedTable.value],
	() => {
		if (!expandedDataSource.value || !expandedTable.value) {
			return
		}
		const table = dataSourceTables.value[expandedDataSource.value].find(
			(t) => t.name === expandedTable.value
		)
		if (!table) {
			return
		}
		tableStore.getTableColumns(expandedDataSource.value, table.table_name).then((columns) => {
			expandedTableColumns.value = toOptions(columns, {
				label: 'name',
				value: 'name',
				description: 'type',
			})
		})
	}
)
function toggleExpandedTable(table: string) {
	if (expandedTable.value === table) {
		expandedTable.value = null
	} else {
		tableRestrictions.value[table] = tableRestrictions.value[table] || ''
		expandedTable.value = table
	}
}
</script>

<template>
	<div
		v-for="data_source in dataSources"
		:key="data_source.name"
		class="flex flex-col pr-2"
		:data-source="data_source.name"
	>
		<div class="sticky top-0 z-10 flex items-center gap-2 bg-white py-1.5">
			<FormControl
				type="checkbox"
				:modelValue="isDataSourceSelected(data_source.name)"
				@update:modelValue="selectDataSource(data_source.name, $event)"
			/>
			<div
				class="group flex flex-1 cursor-pointer items-center justify-between gap-2"
				@click="toggleExpandedDataSource(data_source.name)"
			>
				<div class="flex flex-shrink-0 select-none items-baseline gap-2">
					<p class="group-hover:underline">
						{{ data_source.title }}
					</p>
					<p
						v-if="selectedTables[data_source.name]?.length"
						class="text-p-xs text-gray-700"
					>
						({{ selectedTables[data_source.name]?.length }} selected)
					</p>
				</div>
				<hr class="flex-1 border-gray-200" />
				<component
					:is="expandedDataSource === data_source.name ? ChevronDown : ChevronRight"
					class="h-4 w-4 flex-shrink-0 text-gray-600"
					stroke-width="1.5"
				/>
			</div>
		</div>
		<div
			v-if="expandedDataSource === data_source.name"
			class="flex flex-col gap-2.5 pl-6 pb-1.5"
		>
			<FormControl
				type="text"
				placeholder="Search tables"
				v-model="tableSearchQuery"
				autocomplete="off"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-600" stroke-width="1.5" />
				</template>
				<template #suffix>
					<LoadingIndicator v-if="tableStore.loading" class="h-4 w-4 text-gray-600" />
				</template>
			</FormControl>
			<div
				v-for="table in expandedDataSourceTables
					.filter((t) =>
						t.table_name.toLocaleLowerCase().includes(tableSearchQuery.toLowerCase())
					)
					.slice(0, 50)"
				:key="table.name"
			>
				<div class="flex flex-col gap-1">
					<div class="group flex items-center gap-2">
						<FormControl
							type="checkbox"
							:modelValue="isTableSelected(data_source.name, table.name)"
							@update:modelValue="selectTable(data_source.name, table.name, $event)"
						/>
						<div
							class="group flex flex-shrink-0 select-none items-baseline gap-2"
							@click="
								selectTable(
									data_source.name,
									table.name,
									!isTableSelected(data_source.name, table.name)
								)
							"
						>
							<p class="leading-5">{{ table.table_name }}</p>
							<p
								v-if="
									isTableSelected(data_source.name, table.name) ||
									expandedTable === table.name ||
									tableRestrictions[table.name]
								"
								class="invisible cursor-pointer text-xs leading-5 text-gray-600 transition-all hover:underline group-hover:visible"
								:class="
									expandedTable === table.name || tableRestrictions[table.name]
										? '!visible'
										: 'invisible'
								"
								@click.prevent.stop="toggleExpandedTable(table.name)"
							>
								{{
									expandedTable === table.name
										? 'Hide'
										: tableRestrictions[table.name]
										? 'Edit Filters'
										: 'Set Filters'
								}}
							</p>
						</div>
					</div>
					<div v-if="expandedTable === table.name" class="ml-6 flex flex-col gap-1.5">
						<ExpressionEditor
							:column-options="expandedTableColumns"
							v-model="tableRestrictions[table.name]"
							placeholder="eg. country == 'India'"
							class="h-fit max-h-[10rem] min-h-[2.5rem] text-sm"
						/>
					</div>
				</div>
			</div>
			<div v-if="expandedDataSourceTables.length > 50" class="text-xs text-gray-600">
				Showing only 50 of {{ expandedDataSourceTables.length }} tables
			</div>
			<div v-if="!expandedDataSourceTables.length" class="text-xs text-gray-600">
				No tables found
			</div>
		</div>
	</div>
</template>
