import { useQueryResource } from '@/query/useQueryResource'
import sessionStore from '@/stores/sessionStore'
import settingsStore from '@/stores/settingsStore'
import { areDeeplyEqual, createTaskRunner } from '@/utils'
import { useQueryColumns } from '@/utils/query/columns'
import { useQueryFilters } from '@/utils/query/filters'
import { getFormattedResult } from '@/utils/query/results'
import { useQueryTables } from '@/utils/query/tables'
import { whenever } from '@vueuse/core'
import { debounce } from 'frappe-ui'
import { computed, reactive } from 'vue'
import useChart from './useChart'

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
		chart: {},
		formattedResults: [],
		resultColumns: [],
		sourceSchema: {},
	})

	const run = createTaskRunner()
	state.doc = computed(() => resource.doc)

	const setLoading = (value) => (state.loading = value)

	// Results
	state.MAX_ROWS = 100
	state.formattedResults = computed(() => getFormattedResult(resource.doc.results))
	state.resultColumns = computed(() => resource.doc.results?.[0])
	state.isOwner = computed(() => resource.doc?.owner === session.user.user_id)

	state.reload = () => {
		setLoading(true)
		return resource.get
			.fetch()
			.then(() => state.doc.chart && useChart(state.doc.chart))
			.then((chart) => (state.chart = chart || {}))
			.finally(() => setLoading(false))
	}

	state.updateTitle = (title) => {
		setLoading(true)
		return run(() => resource.setValue.submit({ title }).finally(() => setLoading(false)))
	}
	state.changeDataSource = (data_source) => {
		setLoading(true)
		return run(() => resource.setValue.submit({ data_source }).then(() => setLoading(false)))
	}

	const autoExecuteEnabled = settingsStore().settings.auto_execute_query
	state.updateQuery = async (newQuery) => {
		if (areDeeplyEqual(newQuery, resource.originalDoc.json))
			return Promise.resolve({ query_updated: false })

		setLoading(true)
		return new Promise((resolve) =>
			run(() =>
				resource.setValue
					.submit({ json: JSON.stringify(newQuery, null, 2) })
					.then(() => autoExecuteEnabled && state.execute())
					.then(() => resolve({ query_updated: true }))
					.finally(() => setLoading(false))
			)
		)
	}

	state.execute = debounce(async () => {
		if (!state.doc?.data_source) return
		setLoading(true)
		state.executing = true
		await run(() => resource.run.submit().catch(() => {}))
		state.executing = false
		setLoading(false)
	}, 500)

	state.updateTransforms = debounce(async (transforms) => {
		if (!transforms) return
		setLoading(true)
		return run(() =>
			resource.setValue
				.submit({ transforms, status: 'Pending Execution' })
				.then(() => autoExecuteEnabled && state.execute())
				.finally(() => setLoading(false))
		)
	}, 500)

	state.duplicate = async () => {
		state.duplicating = true
		await run(() => resource.duplicate.submit())
		state.duplicating = false
		return resource.duplicate.data.message
	}

	state.delete = async () => {
		state.deleting = true
		await run(() => resource.delete.submit())
		state.deleting = false
	}

	state.store = () => {
		setLoading(true)
		return run(() => resource.store.submit().finally(() => setLoading(false)))
	}
	state.unstore = () => {
		setLoading(true)
		return run(() => resource.unstore.submit().finally(() => setLoading(false)))
	}
	state.switchQueryBuilder = () => {
		return run(() => {
			return resource.switch_query_type.submit().then(() => {
				window.location.reload()
			})
		})
	}
	// classic query
	const isClassicQuery = computed(() => {
		if (!resource.doc) return false
		return (
			!resource.doc?.is_assisted_query &&
			!resource.doc?.is_native_query &&
			!resource.doc?.is_script_query
		)
	})
	whenever(isClassicQuery, () => {
		if (state.classicQueryInitialized || !isClassicQuery.value) return

		state.addTable = resource.addTable
		state.fetchTables = resource.fetchTables
		state.updateTable = resource.updateTable
		state.removeTable = resource.removeTable
		state.fetchJoinOptions = resource.fetchJoinOptions
		state.tables = useQueryTables(state)

		state.addColumn = resource.addColumn
		state.moveColumn = resource.moveColumn
		state.removeColumn = resource.removeColumn
		state.updateColumn = resource.updateColumn
		state.fetchColumns = resource.fetchColumns
		state.columns = useQueryColumns(state)

		state.updateFilters = resource.updateFilters
		state.fetchColumnValues = resource.fetchColumnValues
		state.filters = useQueryFilters(state)
		state.classicQueryInitialized = true
	})

	state.convertToNative = async () => {
		if (state.doc.is_native_query) return
		setLoading(true)
		return run(() => {
			return resource.setValue
				.submit({ is_native_query: 1, is_assisted_query: 0, is_script_query: 0 })
				.finally(() => setLoading(false))
		})
	}

	// native query
	state.executeSQL = debounce((sql) => {
		if (!sql || sql === state.doc.sql) return state.execute()
		setLoading(true)
		return run(() =>
			resource.setValue
				.submit({ sql })
				.then(() => state.execute())
				.finally(() => setLoading(false))
		)
	}, 500)

	// script query
	state.updateScript = debounce((script) => {
		if (script === state.doc.script) return
		setLoading(true)
		return run(() => resource.setValue.submit({ script }).finally(() => setLoading(false)))
	}, 500)

	state.updateScriptVariables = debounce((script_variables) => {
		if (variables === state.doc.variables) return
		setLoading(true)
		return run(() => resource.setValue.submit({ variables }).finally(() => setLoading(false)))
	}, 500)

	return state
}
