import { useQueryResource } from '@/query/useQueryResource'
import sessionStore from '@/stores/sessionStore'
import settingsStore from '@/stores/settingsStore'
import { areDeeplyEqual, createTaskRunner } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { debounce } from 'frappe-ui'
import { computed, reactive } from 'vue'

const session = sessionStore()

const queries = {}

export default function useQuery(name) {
	if (!queries[name]) {
		queries[name] = makeQuery(name)
	}
	return queries[name]
}

function makeQuery(name) {
	const resource = useQueryResource(name)
	const state = reactive({
		loading: true,
		executing: false,
		doc: {},
		formattedResults: [],
		resultColumns: [],
		tableMeta: [],
		columnOptions: [],
	})

	const run = createTaskRunner()
	state.doc = computed(() => resource.doc)
	state.loading = computed(() => resource.loading)

	// Results
	state.MAX_ROWS = 100
	state.formattedResults = computed(() => getFormattedResult(resource.doc.results))
	state.resultColumns = computed(() => resource.doc.results?.[0])

	state.reload = () => resource.get.fetch()
	state.reload().then(() => state.fetchTableMeta())

	state.updateTitle = (title) => run(() => resource.setValue.submit({ title }))
	state.changeDataSource = (data_source) => run(() => resource.setValue.submit({ data_source }))

	state.updateQuery = debounce(async (newQuery) => {
		if (areDeeplyEqual(newQuery, state.doc.json)) return
		const tablesChanged = hasTablesChanged(newQuery, state.doc.json)
		const autoExecuteEnabled = settingsStore().settings.auto_execute_query

		await run(() =>
			resource.setValue
				.submit({ json: newQuery })
				.then(() => autoExecuteEnabled && state.execute())
				.then(() => tablesChanged && state.fetchTableMeta())
		)
	}, 500)

	state.execute = debounce(async () => {
		state.executing = true
		await run(() => resource.run.submit())
		state.executing = false
	}, 500)

	state.getChartName = async () => {
		const response = await resource.get_chart_name.fetch()
		return response.message
	}

	state.fetchTableMeta = async () => {
		if (!state.doc.data_source) return
		// no need to use `run` here because this doesn't change the doc
		const res = await resource.fetch_table_meta.submit()
		state.tableMeta = res.message
		state.columnOptions = makeColumnOptions(state.tableMeta)
	}

	return state
}

function hasTablesChanged(newJson, oldJson) {
	if (!oldJson) return true
	const newTables = [newJson.table.table, ...newJson.joins.map((join) => join.right_table.table)]
	const oldTables = [oldJson.table.table, ...oldJson.joins.map((join) => join.right_table.table)]
	return JSON.stringify(newTables) != JSON.stringify(oldTables)
}

function makeColumnOptions(tableMeta) {
	return tableMeta.map((table) => {
		const countColumn = {
			table: table.table,
			column: 'count',
			type: 'Integer',
			label: `${table.label} Count`,
			alias: `${table.label} Count`,
			order: '',
			granularity: '',
			aggregation: 'count',
			format: {},
			expression: {},
			description: 'Integer',
			value: `${table.table}.count`,
		}
		return {
			group: table.label,
			items: [
				countColumn,
				...table.columns.map((column) => {
					return {
						...column,
						description: column.type,
						value: `${table.table}.${column.column}`,
					}
				}),
			],
		}
	})
}
