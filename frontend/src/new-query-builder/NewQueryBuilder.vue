<script setup>
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import Tabs from '@/components/Tabs.vue'
import { safeJSONParse } from '@/utils'
import { LoadingIndicator } from 'frappe-ui'
import { computed, inject, nextTick, onMounted, provide, reactive, ref, watch } from 'vue'
import ChartOptions from './ChartOptions.vue'
import ChartSection from './ChartSection.vue'
import ColumnSection from './ColumnSection.vue'
import FilterSection from './FilterSection.vue'
import QueryHeader from './QueryHeader.vue'
import ResultColumnActions from './ResultColumnActions.vue'
import ResultFooter from './ResultFooter.vue'
import ResultSection from './ResultSection.vue'
import TableSection from './TableSection.vue'
import TransformSection from './TransformSection.vue'
import { NEW_FILTER } from './constants'
import { ERROR_UNABLE_TO_INFER_JOIN, ERROR_UNABLE_TO_RESET_MAIN_TABLE } from './messages'
import useChart from './useChart'
import useQuery from './useQuery'
import {
	inferJoinForTable,
	inferJoinsFromColumns,
	isTableAlreadyAdded,
	makeNewColumn,
} from './utils'

const props = defineProps({ name: String })
const query = useQuery(props.name)
provide('query', query)

const builder = reactive({
	data_source: computed(() => query.doc.data_source),
	query: {
		table: {},
		joins: [],
		columns: [],
		filters: [],
		calculations: [],
		dimensions: [],
		measures: [],
		orders: [],
		limit: 100,
	},
	transforms: computed(() => [...query.doc.transforms]),
	chart: {},
	addTable,
	resetMainTable,
	removeJoinAt,
	updateJoinAt,
	addColumns,
	removeColumnAt,
	updateColumnAt,
	addFilter,
	removeFilterAt,
	updateFilterAt,
	addTransform,
	removeTransformAt,
	updateTransformAt,
	setOrderBy,
})
provide('builder', builder)
watch(() => builder.query, query.updateQuery, { deep: true })
onMounted(() => query.doc?.json && (builder.query = safeJSONParse({ ...query.doc.json })))

const activeTab = ref('Build')
const tabs = ['Build', 'Visualize']

builder.chart = await useChart(query)
watch(() => builder.chart.doc, builder.chart.updateDoc, { deep: true })

const $notify = inject('$notify')
function addTable(newTable) {
	const mainTable = builder.query.table
	if (!mainTable?.table) {
		builder.query.table = { table: newTable.table, label: newTable.label }
		nextTick(() => query.execute())
		return
	}
	if (isTableAlreadyAdded(builder.query, newTable)) return
	const join = inferJoinForTable(newTable, builder.query, query.tableMeta)
	if (!join) {
		$notify(ERROR_UNABLE_TO_INFER_JOIN(mainTable.label, newTable.label))
		return
	}
	builder.query.joins.push(join)
}

function resetMainTable() {
	if (builder.query.joins.length || builder.query.columns.length) {
		$notify(ERROR_UNABLE_TO_RESET_MAIN_TABLE())
		return
	}
	builder.query.table = {}
}

function removeJoinAt(joinIdx) {
	builder.query.joins.splice(joinIdx, 1)
}

function updateJoinAt(joinIdx, newJoin) {
	builder.query.joins.splice(joinIdx, 1, newJoin)
}

function addColumns(addedColumns) {
	const newColumns = addedColumns.map(makeNewColumn)
	builder.query.columns.push(...newColumns)
	builder.query.joins = inferJoinsFromColumns(builder.query, query.tableMeta)
}

function removeColumnAt(removedColumnIdx) {
	builder.query.columns.splice(removedColumnIdx, 1)
	builder.query.joins = inferJoinsFromColumns(builder.query, query.tableMeta)
}

function updateColumnAt(updatedColumnIdx, newColumn) {
	builder.query.columns.splice(updatedColumnIdx, 1, newColumn)
	builder.query.joins = inferJoinsFromColumns(builder.query, query.tableMeta)
}

function addFilter() {
	builder.query.filters.push({ ...NEW_FILTER })
	builder.query.joins = inferJoinsFromColumns(builder.query, query.tableMeta)
}
function removeFilterAt(removedFilterIdx) {
	builder.query.filters.splice(removedFilterIdx, 1)
	builder.query.joins = inferJoinsFromColumns(builder.query, query.tableMeta)
}
function updateFilterAt(updatedFilterIdx, newFilter) {
	builder.query.filters.splice(updatedFilterIdx, 1, newFilter)
	builder.query.joins = inferJoinsFromColumns(builder.query, query.tableMeta)
}

function addTransform() {
	builder.transforms.push({ type: '', options: {} })
	query.updateTransforms(builder.transforms)
}
function removeTransformAt(removedTransformIdx) {
	builder.transforms.splice(removedTransformIdx, 1)
	query.updateTransforms(builder.transforms)
}
function updateTransformAt(updatedTransformIdx, newTransform) {
	builder.transforms.splice(updatedTransformIdx, 1, newTransform)
	query.updateTransforms(builder.transforms)
}

function setOrderBy(column, order) {
	builder.query.columns.some((c) => {
		if (c.label === column) {
			c.order = order
			return true
		}
	})
}
</script>

<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs class="h-7" :items="[{ label: 'Queries' }, { label: query.doc?.name }]" />
	</header>
	<div v-if="query.doc?.name" class="flex h-full w-full flex-col space-y-4 overflow-hidden pt-2">
		<div class="px-6">
			<QueryHeader></QueryHeader>
		</div>
		<div class="relative flex flex-1 flex-row-reverse overflow-hidden border-t">
			<div
				v-if="query.loading"
				class="absolute inset-0 z-10 flex items-center justify-center bg-gray-100/50"
			>
				<LoadingIndicator class="w-10 text-gray-600" />
			</div>
			<div class="flex h-full w-full flex-col space-y-4 overflow-hidden p-4">
				<div class="flex flex-[3] flex-shrink-0 flex-col overflow-hidden">
					<ChartSection></ChartSection>
				</div>
				<div class="flex flex-[2] flex-shrink-0 flex-col overflow-hidden">
					<ResultSection>
						<template #columnActions="{ column }">
							<ResultColumnActions :column="column" />
						</template>
						<template #footer>
							<ResultFooter></ResultFooter>
						</template>
					</ResultSection>
				</div>
			</div>

			<div
				class="flex w-[21rem] flex-shrink-0 flex-col space-y-4 overflow-y-scroll border-r bg-white p-4"
			>
				<Tabs v-model="activeTab" class="w-full flex-shrink-0" :tabs="tabs" />
				<template v-if="activeTab === 'Build'">
					<TableSection></TableSection>
					<hr class="border-gray-200" />
					<FilterSection></FilterSection>
					<hr class="border-gray-200" />
					<ColumnSection></ColumnSection>
					<hr class="border-gray-200" />
					<TransformSection></TransformSection>
				</template>
				<template v-if="activeTab === 'Visualize'">
					<ChartOptions></ChartOptions>
				</template>
			</div>
		</div>
	</div>
</template>
