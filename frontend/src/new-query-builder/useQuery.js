import useChart from '@/query/useChart'
import { useQueryResource } from '@/query/useQueryResource'
import sessionStore from '@/stores/sessionStore'
import settingsStore from '@/stores/settingsStore'
import { safeJSONParse } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { watchDebounced, watchOnce } from '@vueuse/core'
import { call, debounce } from 'frappe-ui'
import { computed, reactive, watch } from 'vue'

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
		autosave: false,
		loading: true,
		executing: false,
		error: null,
		isOwner: false,
		doc: {},
		chart: {},
		sourceSchema: [],
		formattedResults: [],
		resultColumns: [],
		tableMeta: [],
		columnOptions: [],
	})

	state.reload = async () => {
		await resource.get.fetch()
		state.syncDoc()
		state.loading = false
	}
	state.reload()

	state.syncDoc = function () {
		state.doc = { ...resource.doc }
	}

	state.convertToNative = async function () {
		state.loading = true
		await resource.convert_to_native.submit()
		await state.syncDoc()
		state.loading = false
	}
	state.convertToAssisted = async function () {
		state.loading = true
		await resource.convert_to_assisted.submit()
		await state.syncDoc()
		state.loading = false
	}

	// Results
	state.MAX_ROWS = 100
	state.formattedResults = computed(() =>
		getFormattedResult(state.doc.results.slice(0, state.MAX_ROWS))
	)
	state.resultColumns = computed(() => state.doc.results?.[0])

	state.execute = debounce(async () => {
		state.executing = true
		await resource.run
			.submit()
			.then(() => state.syncDoc())
			.catch((e) => console.error(e))
		state.executing = false
	}, 300)

	watchOnce(() => state.autosave, setupAutosaveListener)
	function setupAutosaveListener() {
		watchDebounced(
			getUpdatedFields,
			function (newDoc, oldDoc) {
				if (!oldDoc || !newDoc) return
				if (state.saveWhenSavingIsDone) return
				if (JSON.stringify(newDoc) == JSON.stringify(oldDoc)) return
				if (state.saving || state.executing) {
					state.saveWhenSavingIsDone = true
					return
				}
				state.save()
			},
			{ deep: true, debounce: 500 }
		)

		watch(
			() => state.saving,
			(newSaving, oldSaving) => {
				const wasSaving = !newSaving && oldSaving
				if (wasSaving && state.saveWhenSavingIsDone) {
					state.saveWhenSavingIsDone = false
					state.save()
				}
			}
		)
	}

	function getUpdatedFields() {
		if (!state.doc.data_source) return
		const updatedFields = {
			title: state.doc.title,
			data_source: state.doc.data_source,
			sql: state.doc.sql || '',
			script: state.doc.script || '',
			json: JSON.stringify(safeJSONParse(state.doc.json), null, 2),
		}
		return updatedFields
	}

	const autoExecuteQuery = computed(() => settingsStore().settings.auto_execute_query)
	state.save = async () => {
		state.loading = true
		state.saving = true
		await resource.setValue.submit(getUpdatedFields()).then(() => state.syncDoc())
		if (
			autoExecuteQuery.value &&
			!state.executing &&
			resource.doc.status == 'Pending Execution'
		) {
			await state.execute()
		}
		state.saving = false
		state.loading = false
	}

	state.fetchSourceSchema = async () => {
		if (!state.doc.data_source) return
		state.sourceSchema = await call('insights.api.data_sources.get_source_schema', {
			data_source: state.doc.data_source,
		})
	}

	state.loadChart = async () => {
		const response = await resource.get_chart_name.fetch()
		state.chart = useChart(response.message)
		state.chart.enableAutoSave()
	}
	state.getChartName = async () => {
		const response = await resource.get_chart_name.fetch()
		return response.message
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
		state.syncDoc()
		state.loading = false
	}

	state.duplicate = async () => {
		state.duplicating = true
		const res = await resource.duplicate.submit()
		state.duplicating = false
		return res.message
	}

	state.saveAsTable = async () => {
		state.loading = true
		await resource.save_as_table.submit()
		state.syncDoc()
		state.loading = false
	}

	state.fetchTableMeta = async () => {
		if (!state.doc.data_source) return
		const res = await resource.fetch_table_meta.submit()
		state.tableMeta = res.message
	}
	watch(
		() => state.doc.json,
		(newVal, oldVal) => {
			const newJson = safeJSONParse(newVal)
			const oldJson = safeJSONParse(oldVal)
			if (JSON.stringify(newJson) == JSON.stringify(oldJson)) return
			if (
				JSON.stringify(newJson?.tables) == JSON.stringify(oldJson?.tables) &&
				JSON.stringify(newJson?.joins) == JSON.stringify(oldJson?.joins)
			)
				return

			state.fetchTableMeta()
		},
		{ deep: true, immediate: true }
	)

	watch(
		() => state.tableMeta,
		(newMeta, oldMeta) => {
			if (!newMeta) return
			if (!state.tableMeta.length) return
			if (JSON.stringify(newMeta) == JSON.stringify(oldMeta)) return
			state.columnOptions = state.tableMeta.map((table) => {
				return {
					group: table.label,
					items: table.columns.map((column) => {
						return {
							...column,
							description: column.type,
							value: `${table.table}.${column.column}`,
						}
					}),
				}
			})
		},
		{ deep: true, immediate: true }
	)

	return state
}
