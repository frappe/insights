import useChart from '@/query/useChart'
import { safeJSONParse, useAutoSave } from '@/utils'
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
		})
	}
	refresh()

	state.convertToNative = async function () {
		state.loading = true
		await resource.convert_to_native.submit()
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
				state.executing = false
			})
		state.executing = false
	}, 300)

	state.save = async () => {
		state.loading = true
		delete state.doc.modified
		await resource.setValue.submit({ ...state.doc })
		state.loading = false
	}

	watchOnce(
		() => state.autosave,
		() => {
			const fieldsToWatch = computed(() => {
				// if doc is not loaded, don't watch
				if (state.loading) return

				const is_native_query = state.doc.is_native_query
				return is_native_query
					? {
							sql: state.doc.sql,
							data_source: state.doc.data_source,
					  }
					: {}
			})
			useAutoSave(fieldsToWatch, {
				saveFn: state.save,
				interval: 2000,
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
			convert_to_native: 'convert_to_native',
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
