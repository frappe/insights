import { useAutoSave } from '@/utils'
import useChart from '@/query/useChart'
import { safeJSONParse } from '@/utils'
import auth from '@/utils/auth'
import { getFormattedResult } from '@/utils/query/results'
import { watchOnce } from '@vueuse/core'
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
		loading: true,
		executing: false,
		error: null,
		isOwner: false,
		doc: {
			data_source: '',
			name,
			sql: '',
		},
		chart: {},
		sourceSchema: [],
		formattedResults: [],
	})

	async function refresh() {
		return resource.get.fetch().then((doc) => {
			state.doc = doc
			state.isOwner = state.doc.owner == auth.user.user_id
			state.loading = false
		})
	}
	refresh()

	// Results
	state.MAX_ROWS = 500
	state.formattedResults = computed(() => getFormattedResult(state.doc.results))
	state.resultColumns = computed(() => state.doc.results?.[0])

	state.execute = debounce(async () => {
		state.executing = true
		await resource.setValue.submit({
			is_native_query: 1,
			sql: state.doc.sql,
			data_source: state.doc.data_source,
		})
		await resource.run.submit()
		await refresh()
		state.executing = false
	}, 300)

	state.save = async () => {
		state.loading = true
		await resource.setValue.submit({
			is_native_query: 1,
			sql: state.doc.sql,
			data_source: state.doc.data_source,
		})
		state.loading = false
	}

	watchOnce(
		() => state.autosave,
		() => {
			const fieldsToWatch = computed(() => {
				// if doc is not loaded, don't watch
				if (state.loading) return
				return {
					sql: state.doc.sql,
					data_source: state.doc.data_source,
				}
			})
			useAutoSave(fieldsToWatch, {
				saveFn: state.save,
				interval: 1500,
			})
		}
	)

	state.fetchSourceSchema = async () => {
		const response = await resource.get_source_schema.fetch()
		state.sourceSchema = response.message
	}

	state.loadChart = async () => {
		const response = await resource.get_chart_name.fetch()
		state.chart = useChart(response.message)
		state.chart.autosave = true
	}

	state.delete = async () => {
		state.deleting = true
		await resource.delete.submit()
		state.deleting = false
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
		},
		transform(doc) {
			doc.columns = doc.columns.map((c) => {
				c.format_option = safeJSONParse(c.format_option, {})
				return c
			})
			doc.results = safeJSONParse(doc.results)
			return doc
		},
	})
	return resource
}
