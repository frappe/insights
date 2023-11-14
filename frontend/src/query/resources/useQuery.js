import { useQueryResource } from '@/query/useQueryResource'
import sessionStore from '@/stores/sessionStore'
import settingsStore from '@/stores/settingsStore'
import { areDeeplyEqual, createTaskRunner } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
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
	})

	const run = createTaskRunner()
	state.doc = computed(() => resource.doc)
	state.loading = computed(() => resource.loading)

	// Results
	state.MAX_ROWS = 100
	state.formattedResults = computed(() => getFormattedResult(resource.doc.results))
	state.resultColumns = computed(() => resource.doc.results?.[0])

	state.reload = () => {
		return resource.get
			.fetch()
			.then(() => useChart(state))
			.then((chart) => (state.chart = chart))
	}

	state.updateTitle = (title) => run(() => resource.setValue.submit({ title }))
	state.changeDataSource = (data_source) => run(() => resource.setValue.submit({ data_source }))

	const autoExecuteEnabled = settingsStore().settings.auto_execute_query
	state.updateQuery = async (newQuery) => {
		if (areDeeplyEqual(newQuery, resource.originalDoc.json)) return Promise.resolve()
		return new Promise((resolve) =>
			run(() =>
				resource.setValue
					.submit({ json: JSON.stringify(newQuery, null, 2) })
					.then(() => autoExecuteEnabled && state.execute())
					.then(resolve)
			)
		)
	}

	state.execute = debounce(async () => {
		state.executing = true
		await run(() => resource.run.submit().catch(() => {}))
		state.executing = false
	}, 500)

	state.getChartName = async () => {
		const response = await resource.get_chart_name.fetch()
		return response.message
	}

	state.updateTransforms = debounce(async (transforms) => {
		if (!transforms) return
		return run(() =>
			resource.setValue
				.submit({ transforms })
				.then(() => autoExecuteEnabled && state.execute())
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

	state.store = () => run(() => resource.store.submit())
	state.save_as_table = () => run(() => resource.save_as_table.submit())
	state.delete_linked_table = () => run(() => resource.delete_linked_table.submit())

	// native query
	state.updateSQL = debounce(async (sql) => {
		if (sql === state.doc.sql) return
		await run(() =>
			resource.setValue.submit({ sql }).then(() => autoExecuteEnabled && state.execute())
		)
	}, 500)

	// script query
	state.updateScript = debounce(async (script) => {
		if (script === state.doc.script) return
		await run(() =>
			resource.setValue.submit({ script }).then(() => autoExecuteEnabled && state.execute())
		)
	}, 500)

	state.updateScriptVariables = debounce(async (script_variables) => {
		if (variables === state.doc.variables) return
		await run(() =>
			resource.setValue
				.submit({ variables })
				.then(() => autoExecuteEnabled && state.execute())
		)
	}, 500)

	return state
}
