import useChart from '@/query/useChart'
import { useQueryResource } from '@/query/useQueryResource'
import { safeJSONParse } from '@/utils'
import auth from '@/utils/auth'
import { getFormattedResult } from '@/utils/query/results'
import { watchDebounced, watchOnce } from '@vueuse/core'
import { debounce, call } from 'frappe-ui'
import { computed, reactive } from 'vue'

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

	state.reload = async function () {
		return resource.get.fetch().then((doc) => {
			state.doc = doc
			state.isOwner = state.doc.owner == auth.user.user_id
			state.loading = false
			state.unsaved = false
		})
	}
	state.reload()

	state.convertToNative = async function () {
		state.loading = true
		await resource.convert_to_native.submit()
		await state.reload()
		state.loading = false
	}
	state.convertToAssisted = async function () {
		state.loading = true
		await resource.convert_to_assisted.submit()
		await state.reload()
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
			.then(() => state.reload())
			.catch((e) => {
				console.error(e)
			})
		state.executing = false
	}, 300)

	state.save = async () => {
		state.loading = true
		const updatedFields = getUpdatedFields()
		await resource.setValue.submit(updatedFields)
		await state.reload()
		state.loading = false
	}

	function getUpdatedFields() {
		if (!state.doc.data_source) return
		if (state.doc.is_native_query) {
			return {
				sql: state.doc.sql,
				data_source: state.doc.data_source,
				title: state.doc.title,
			}
		} else {
			return {
				json: JSON.stringify(safeJSONParse(state.doc.json), null, 2),
				data_source: state.doc.data_source,
				title: state.doc.title,
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
			watchDebounced(getUpdatedFields, saveIfChanged, { deep: true, debounce: 1000 })
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
		state.sourceSchema = await call('insights.api.get_source_schema', {
			data_source: state.doc.data_source,
		})
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

	state.updateDoc = async (doc) => {
		state.loading = true
		await resource.setValue.submit(doc)
		await state.reload()
		state.loading = false
	}

	state.duplicate = async () => {
		state.duplicating = true
		const { message } = await resource.duplicate.submit()
		state.duplicating = false
		return message
	}

	return state
}
