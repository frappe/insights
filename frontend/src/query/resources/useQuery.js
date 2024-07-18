import { useQueryResource } from '@/query/useQueryResource'
import sessionStore from '@/stores/sessionStore'
import settingsStore from '@/stores/settingsStore'
import { areDeeplyEqual, createTaskRunner } from '@/utils'
import { useQueryColumns } from '@/utils/query/columns'
import { useQueryFilters } from '@/utils/query/filters'
import { useQueryTables } from '@/utils/query/tables'
import { createToast } from '@/utils/toasts'
import { whenever } from '@vueuse/core'
import { debounce } from 'frappe-ui'
import { computed, reactive } from 'vue'
import useQueryChart from './useQueryChart'
import useQueryResults from './useQueryResults'

const session = sessionStore()

export default function useQuery(name) {
	const resource = useQueryResource(name)
	const state = reactive({
		loading: true,
		executing: false,
		doc: {},
		chart: {},
		results: {},
		sourceSchema: {},
	})

	const queue = createTaskRunner()
	state.doc = computed(() => resource.doc)

	const setLoading = (value) => (state.loading = value)

	// Results
	state.MAX_ROWS = 100
	state.isOwner = computed(() => resource.doc?.owner === session.user.user_id)

	state.reload = () => {
		setLoading(true)
		return resource.get
			.fetch()
			.then(() => initChartAndResults())
			.finally(() => setLoading(false))
	}

	async function initChartAndResults() {
		if (state.doc.result_name) {
			state.results = useQueryResults(state.doc.result_name)
		}
		if (state.doc.chart) {
			state.chart = useQueryChart(state.doc.chart, state.doc.title, state.results)
		}
	}

	state.updateTitle = (title) => {
		setLoading(true)
		return queue(() => resource.setValue.submit({ title }).finally(() => setLoading(false)))
	}
	state.changeDataSource = (data_source) => {
		setLoading(true)
		return queue(() => resource.setValue.submit({ data_source }).then(() => setLoading(false)))
	}

	const autoExecuteEnabled = settingsStore().settings.auto_execute_query
	state.updateQuery = async (newQuery) => {
		if (areDeeplyEqual(newQuery, resource.originalDoc.json))
			return Promise.resolve({ query_updated: false })

		setLoading(true)
		return new Promise((resolve) =>
			queue(() =>
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
		await queue(() => resource.run.submit().catch(() => {}))
		await state.results.reload()
		state.executing = false
		setLoading(false)
	}, 500)

	state.updateTransforms = debounce(async (transforms) => {
		if (!transforms) return
		setLoading(true)
		const updateTransform = () => resource.setValue.submit({ transforms })
		const updateStatus = () => resource.set_status.submit({ status: 'Pending Execution' })
		const autoExecute = () => autoExecuteEnabled && state.execute()
		return queue(() =>
			updateTransform()
				.then(updateStatus)
				.then(autoExecute)
				.finally(() => setLoading(false))
		)
	}, 500)

	state.duplicate = async () => {
		state.duplicating = true
		await queue(() => resource.duplicate.submit())
		state.duplicating = false
		return resource.duplicate.data
	}

	state.delete = async () => {
		state.deleting = true
		await queue(() => resource.delete.submit())
		state.deleting = false
	}

	state.store = () => {
		setLoading(true)
		return queue(() => resource.store.submit().finally(() => setLoading(false)))
	}
	state.unstore = () => {
		setLoading(true)
		return queue(() => resource.unstore.submit().finally(() => setLoading(false)))
	}
	state.switchQueryBuilder = () => {
		return queue(() => {
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
		return queue(() => {
			return resource.setValue
				.submit({ is_native_query: 1, is_assisted_query: 0, is_script_query: 0 })
				.finally(() => setLoading(false))
		})
	}

	// native query
	state.executeSQL = debounce((sql) => {
		if (!sql || sql === state.doc.sql) return state.execute()
		setLoading(true)
		return queue(() =>
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
		return queue(() => resource.setValue.submit({ script }).finally(() => setLoading(false)))
	}, 500)

	state.updateScriptVariables = debounce((variables) => {
		setLoading(true)
		return queue(() =>
			resource.setValue.submit({ variables }).finally(() => {
				createToast({
					title: 'Secret Variables Updated',
				})
				setLoading(false)
			})
		)
	}, 500)

	state.downloadResults = () => {
		const results = state.results?.data
		if (!results || results.length === 0) return
		let data = [...results]
		if (data.length === 0) return
		data[0] = data[0].map((d) => d.label)
		const csvString = data.map((row) => row.join(',')).join('\n')
		const blob = new Blob([csvString], { type: 'text/csv' })
		const url = window.URL.createObjectURL(blob)
		const a = document.createElement('a')
		a.setAttribute('hidden', '')
		a.setAttribute('href', url)
		a.setAttribute('download', `${state.doc.title || 'data'}.csv`)
		document.body.appendChild(a)
		a.click()
		document.body.removeChild(a)
	}

	return state
}
