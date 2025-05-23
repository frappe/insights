import { useDebouncedRefHistory } from '@vueuse/core'
import { computed, reactive, toRefs, watch } from 'vue'
import { copy, copyToClipboard, getUniqueId, safeJSONParse, waitUntil, wheneverChanges } from '../helpers'
import { GranularityType } from '../helpers/constants'
import useDocumentResource from '../helpers/resource'
import { column, count, query_table } from '../query/helpers'
import useQuery, { Query } from '../query/query'
import {
	AXIS_CHARTS,
	AxisChartConfig,
	CHARTS,
	DonutChartConfig,
	NumberChartConfig,
	TableChartConfig,
} from '../types/chart.types'
import { AdhocFilters } from '../types/query.types'
import { InsightsChartv3 } from '../types/workbook.types'
import useWorkbook, { getLinkedQueries } from '../workbook/workbook'
import { handleOldXAxisConfig, handleOldYAxisConfig, setDimensionNames } from './helpers'

const charts = new Map<string, Chart>()

export default function useChart(name: string) {
	const key = String(name)
	const existingChart = charts.get(key)
	if (existingChart) return existingChart

	const chart = makeChart(name)
	charts.set(key, chart)
	return chart
}

function makeChart(name: string) {
	const chart = getChartResource(name)

	chart.onAfterLoad(() => useQuery(chart.doc.data_query))

	wheneverChanges(
		() => chart.doc.query,
		() => chart.isloaded && refresh()
	)

	type ChartRefreshArgs = {
		force?: boolean
		adhocFilters?: AdhocFilters
	}

	const dataQuery = computed(() => {
		if (!chart.isloaded) return {} as Query
		return useQuery(chart.doc.data_query)
	})
	async function refresh(args: ChartRefreshArgs = {}) {
		await waitUntil(
			() => chart.isloaded && dataQuery.value.isloaded && useQuery(chart.doc.query).isloaded
		)

		const isValid = validateConfig()
		if (!isValid) return

		const query = useQuery('new-query-' + getUniqueId())
		addSourceOperation(query)
		addFilterOperation(query)
		addChartOperation(query)
		addOrderByOperation(query)
		addLimitOperation(query)

		const shouldExecute =
			args.force ||
			!dataQuery.value.result.executedSQL ||
			args.adhocFilters ||
			JSON.stringify(query.doc.operations) !== JSON.stringify(dataQuery.value.doc.operations)

		if (!shouldExecute) {
			return
		}

		dataQuery.value.setOperations(copy(query.doc.operations))
		dataQuery.value.doc.use_live_connection = query.doc.use_live_connection
		return dataQuery.value.execute(args.adhocFilters, args.force)
	}

	function validateConfig() {
		const messages = []
		if (!chart.doc.query) {
			messages.push({
				variant: 'error',
				message: 'Query is required',
			})
		}
		if (!chart.doc.chart_type) {
			messages.push({
				variant: 'error',
				message: 'Chart type is required',
			})
		}

		if (!CHARTS.includes(chart.doc.chart_type)) {
			messages.push({
				variant: 'error',
				message: 'Invalid chart type: ' + chart.doc.chart_type,
			})
		}

		if (AXIS_CHARTS.includes(chart.doc.chart_type)) {
			const config = chart.doc.config as AxisChartConfig
			if (!config.x_axis.dimension || !config.x_axis.dimension.column_name) {
				messages.push({
					variant: 'error',
					message: 'X-axis is required',
				})
			}
			if (config.x_axis.dimension.column_name === config.split_by?.dimension.column_name) {
				messages.push({
					variant: 'error',
					message: 'X-axis and Split by cannot be the same',
				})
			}
		}

		if (chart.doc.chart_type === 'Number') {
			const config = chart.doc.config as NumberChartConfig
			if (!config.number_columns?.filter((c) => c.measure_name).length) {
				messages.push({
					variant: 'error',
					message: 'Number column is required',
				})
			}
		}

		if (chart.doc.chart_type === 'Donut' || chart.doc.chart_type === 'Funnel') {
			const config = chart.doc.config as DonutChartConfig
			if (!config.label_column?.column_name) {
				messages.push({
					variant: 'error',
					message: 'Label column is required',
				})
			}
			if (!config.value_column?.measure_name) {
				messages.push({
					variant: 'error',
					message: 'Value column is required',
				})
			}
		}

		if (chart.doc.chart_type === 'Table') {
			const config = chart.doc.config as TableChartConfig
			if (!config.rows?.filter((r) => r.column_name).length) {
				messages.push({
					variant: 'error',
					message: 'Rows are required',
				})
			}
		}

		return !messages.length
	}

	function addSourceOperation(query: Query) {
		query.setSource({
			table: query_table({
				query_name: chart.doc.query,
			}),
		})
	}

	function addFilterOperation(query: Query) {
		if (!chart.doc.config.filters?.filters?.length) return
		query.addFilterGroup(chart.doc.config.filters)
	}

	function addChartOperation(query: Query) {
		if (AXIS_CHARTS.includes(chart.doc.chart_type)) {
			addAxisChartOperation(query)
		}

		if (chart.doc.chart_type === 'Number') {
			addNumberChartOperation(query)
		}

		if (chart.doc.chart_type === 'Donut' || chart.doc.chart_type === 'Funnel') {
			addDonutChartOperation(query)
		}

		if (chart.doc.chart_type === 'Table') {
			addTableChartOperation(query)
		}
	}

	function addAxisChartOperation(query: Query) {
		const config = chart.doc.config as AxisChartConfig

		let values = config.y_axis?.series.map((s) => s.measure).filter((m) => m.measure_name)
		values = values?.length ? values : [count()]

		if (config.split_by?.dimension?.column_name) {
			query.addPivotWider({
				rows: [config.x_axis.dimension],
				columns: [config.split_by.dimension],
				values: values,
				max_column_values: config.split_by.max_split_values || 10,
			})
			return
		}

		query.addSummarize({
			measures: values,
			dimensions: [config.x_axis.dimension],
		})
	}

	function addNumberChartOperation(query: Query) {
		const config = chart.doc.config as NumberChartConfig

		query.addSummarize({
			measures: config.number_columns?.filter((c) => c.measure_name),
			dimensions: config.date_column?.column_name ? [config.date_column] : [],
		})
	}

	function addDonutChartOperation(query: Query) {
		const config = chart.doc.config as DonutChartConfig

		query.addSummarize({
			measures: [config.value_column],
			dimensions: [config.label_column],
		})
		query.addOrderBy({
			column: column(config.value_column.measure_name),
			direction: 'desc',
		})
	}

	function addTableChartOperation(query: Query) {
		const config = chart.doc.config as TableChartConfig

		let rows = config.rows.filter((r) => r.column_name)
		let columns = config.columns.filter((c) => c.column_name)
		let values = config.values.filter((v) => v.measure_name)
		values = values.length ? values : []

		if (columns.length) {
			query.addPivotWider({
				rows: rows,
				columns: columns,
				values: values,
				max_column_values: config.max_column_values || 10,
			})
			return
		}

		query.addSummarize({
			measures: values,
			dimensions: rows,
		})
	}

	function addOrderByOperation(query: Query) {
		chart.doc.config.order_by.forEach((sort) => {
			if (sort.column.column_name && sort.direction) {
				query.addOrderBy({
					column: column(sort.column.column_name),
					direction: sort.direction,
				})
			}
		})
	}

	function addLimitOperation(query: Query) {
		if (chart.doc.config.limit) {
			query.addLimit(chart.doc.config.limit)
		}
	}

	function updateGranularity(column_name: string, granularity: GranularityType) {
		if ('x_axis' in chart.doc.config) {
			if (chart.doc.config.x_axis?.dimension?.dimension_name === column_name) {
				chart.doc.config.x_axis.dimension.granularity = granularity
			}
		}

		if ('date_column' in chart.doc.config) {
			if (chart.doc.config.date_column?.dimension_name === column_name) {
				chart.doc.config.date_column.granularity = granularity
			}
		}

		if ('rows' in chart.doc.config) {
			chart.doc.config.rows.forEach((row) => {
				if (row.dimension_name === column_name) {
					row.granularity = granularity
				}
			})
		}
	}

	function getShareLink() {
		return `${window.location.origin}/insights/shared/chart/${chart.doc.name}`
	}

	function getDependentQueries() {
		return [chart.doc.query, ...getLinkedQueries(chart.doc.query)]
	}

	function getDependentQueryColumns() {
		return getDependentQueries().map((q) => {
			const query = useQuery(q)
			if (!query.result.executedSQL) {
				query.execute()
			}
			return {
				group: query.doc.title,
				items: query.result.columnOptions.map((c) => {
					const sep = '`'
					const value = `${sep}${query.doc.name}${sep}.${sep}${c.value}${sep}`
					return {
						...c,
						value,
					}
				}),
			}
		})
	}

	function resetConfig() {
		// @ts-ignore
		chart.doc.config = {
			order_by: [],
			filters: chart.doc.config.filters,
			limit: chart.doc.config.limit,
		}
	}

	// when chart type changes from axis to non-axis or vice versa reset the config
	watch(
		() => chart.doc.chart_type,
		(newType: string, oldType: string) => {
			if (newType === oldType) return
			if (!newType || !oldType) return
			if (
				(AXIS_CHARTS.includes(newType) && !AXIS_CHARTS.includes(oldType)) ||
				(!AXIS_CHARTS.includes(newType) && AXIS_CHARTS.includes(oldType))
			) {
				resetConfig()
			}
		}
	)

	function copyChart() {
		chart.call('export').then(data => {
			copyToClipboard(JSON.stringify(data, null, 2))
		})
	}

	const history = useDebouncedRefHistory(
		// @ts-ignore
		computed({
			get: () => chart.doc,
			set: (value) => Object.assign(chart.doc, value),
		}),
		{
			deep: true,
			capacity: 100,
			debounce: 500,
		}
	)

	waitUntil(() => chart.isloaded).then(() => {
		wheneverChanges(
			() => chart.doc.title,
			() => {
				if (!chart.doc.workbook) return
				const workbook = useWorkbook(chart.doc.workbook)
				for (const c of workbook.doc.charts) {
					if (c.name === chart.doc.name) {
						c.title = chart.doc.title
						break
					}
				}
			},
			{ debounce: 500 }
		)
	})

	return reactive({
		...toRefs(chart),

		dataQuery,

		refresh,
		updateGranularity,
		resetConfig,

		getShareLink,

		getDependentQueries,
		getDependentQueryColumns,

		copy: copyChart,

		history,
	})
}

export type Chart = ReturnType<typeof makeChart>

const INITIAL_DOC: InsightsChartv3 = {
	doctype: 'Insights Chart v3',
	name: '',
	owner: '',
	title: '',
	workbook: '',
	query: '',
	data_query: '',
	chart_type: '',
	is_public: false,
	config: {} as InsightsChartv3['config'],
	operations: [],
	read_only: false,
}

function getChartResource(name: string) {
	const doctype = 'Insights Chart v3'
	const chart = useDocumentResource<InsightsChartv3>(doctype, name, {
		initialDoc: { ...INITIAL_DOC, name },
		enableAutoSave: true,
		disableLocalStorage: true,
		transform: transformChartDoc,
	})
	wheneverChanges(() => chart.doc.read_only, () => {
		if (chart.doc.read_only) {
			chart.autoSave = false
		}
	})
	return chart
}

function transformChartDoc(doc: any) {
	doc.config = safeJSONParse(doc.config) || {}
	doc.operations = safeJSONParse(doc.operations) || []

	doc.config.filters = doc.config.filters?.filters?.length
		? doc.config.filters
		: {
				filters: [],
				logical_operator: 'And',
		  }
	doc.config.order_by = doc.config.order_by || []
	doc.config.limit = doc.config.limit || 100

	if ('x_axis' in doc.config && doc.config.x_axis) {
		// @ts-ignore
		doc.config.x_axis = handleOldXAxisConfig(doc.config.x_axis)
	}
	if ('y_axis' in doc.config && Array.isArray(doc.config.y_axis)) {
		// @ts-ignore
		doc.config.y_axis = handleOldYAxisConfig(doc.config.y_axis)
	}
	if ('split_by' in doc.config && doc.config.split_by) {
		// @ts-ignore
		doc.config.split_by = handleOldXAxisConfig(doc.config.split_by)
	}
	if (doc.chart_type === 'Funnel') {
		// @ts-ignore
		doc.config.label_position = doc.config.label_position || 'left'
	}

	doc.config = setDimensionNames(doc.config)

	return doc
}

export function newChart() {
	return getChartResource('new-chart-' + getUniqueId())
}
