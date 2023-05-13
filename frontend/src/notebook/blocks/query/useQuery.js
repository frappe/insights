import useChart from '@/query/useChart'
import { safeJSONParse } from '@/utils'
import auth from '@/utils/auth'
import { getFormattedResult } from '@/utils/query/results'
import { watchDebounced, watchOnce } from '@vueuse/core'
import { createDocumentResource, debounce } from 'frappe-ui'
import { computed, reactive } from 'vue'

const queries = {}

export default function useQuery(name) {
	if (!queries[name]) {
		queries[name] = makeQuery(name)
	}
	return queries[name]
}

function makeQuery(name) {
	const resource = getQueryResource(name)
	const state = reactive({
		autosave: false,
		unsaved: false,
		loading: true,
		executing: false,
		error: null,
		isOwner: false,
		doc: {},
		chart: {},
		sourceSchema: [],
		formattedResults: [],
	})

	async function refresh() {
		return resource.get.fetch().then((doc) => {
			state.doc = doc
			state.isOwner = state.doc.owner == auth.user.user_id
			state.loading = false
			state.unsaved = false
		})
	}
	refresh()

	state.convertToNative = async function () {
		state.loading = true
		await resource.convert_to_native.submit()
		await refresh()
		state.loading = false
	}
	state.convertToAssisted = async function () {
		state.loading = true
		await resource.convert_to_assisted.submit()
		await refresh()
		state.loading = false
	}

	// Results
	state.MAX_ROWS = 500
	state.formattedResults = computed(() => getFormattedResult(state.doc.results))
	state.resultColumns = computed(() => state.doc.results?.[0])

	state.execute = debounce(async () => {
		state.executing = true
		await state.save()
		await resource.run
			.submit()
			.then(() => refresh())
			.catch((e) => {
				console.error(e)
			})
		state.executing = false
	}, 300)

	state.save = async () => {
		state.loading = true
		const updatedFields = getUpdatedFields()
		await resource.setValue.submit(updatedFields)
		await refresh()
		state.loading = false
	}

	function getUpdatedFields() {
		if (!state.doc.data_source) return
		if (state.doc.is_native_query) {
			return {
				sql: state.doc.sql,
				data_source: state.doc.data_source,
			}
		} else {
			return {
				json: JSON.stringify(safeJSONParse(state.doc.json), null, 2),
				data_source: state.doc.data_source,
			}
		}
	}

	watchOnce(
		() => state.autosave,
		() => {
			function saveIfChanged(newVal, oldVal) {
				if (!oldVal || !newVal) return
				if (state.loading) return
				if (JSON.stringify(newVal) == JSON.stringify(oldVal)) return
				state.save()
			}
			// TODO: fix the weird bug where the inputs are not selected when auto-saving
			// watchDebounced(getUpdatedFields, saveIfChanged, { deep: true, debounce: 1000 })
		}
	)

	const setUnsaved = (newVal, oldVal) => {
		if (state.unsaved) return
		if (!oldVal || !newVal) return
		if (state.loading) return
		if (JSON.stringify(newVal) == JSON.stringify(oldVal)) return
		state.unsaved = true
	}
	watchDebounced(getUpdatedFields, setUnsaved, { deep: true, debounce: 500 })

	state.fetchSourceSchema = async () => {
		const response = await resource.get_source_schema.fetch()
		state.sourceSchema = response.message
	}

	state.loadChart = async () => {
		const response = await resource.get_chart_name.fetch()
		state.chart = useChart(response.message)
		state.chart.enableAutoSave()
	}

	state.delete = async () => {
		state.deleting = true
		await resource.delete.submit()
		state.deleting = false
	}

	state.getTablesColumns = async () => {
		const response = await resource.get_tables_columns.fetch()
		return response.message
	}

	return state
}

function getQueryResource(name) {
	const resource = createDocumentResource({
		doctype: 'Insights Query',
		name,
		whitelistedMethods: {
			run: 'run',
			get_source_schema: 'get_source_schema',
			get_chart_name: 'get_chart_name',
			convert_to_native: 'convert_to_native',
			convert_to_assisted: 'convert_to_assisted',
			get_tables_columns: 'get_tables_columns',
		},
		transform(doc) {
			doc.columns = doc.columns.map((c) => {
				c.format_option = safeJSONParse(c.format_option, {})
				return c
			})
			doc.results = safeJSONParse(doc.results)
			doc.json = safeJSONParse(doc.json, defaultQueryJSON)
			return doc
		},
	})
	return resource
}

const defaultQueryJSON = {
	table: {},
	joins: [],
	filters: [],
	columns: [],
	calculations: [],
	measures: [],
	dimensions: [],
	orders: [],
	limit: null,
}
