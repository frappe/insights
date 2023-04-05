import { useQuery } from '@/query/useQueries'
import { safeJSONParse } from '@/utils'
import { getFormattedResult } from '@/utils/query/results'
import { watchOnce } from '@vueuse/core'
import { createDocumentResource } from 'frappe-ui'
import { reactive } from 'vue'
import { guessChart } from '@/widgets/useChartData'

export default function useChart(chartName) {
	const resource = getChartResource(chartName)
	const state = reactive({
		query: null,
		data: [],
		loading: false,
		error: null,
		doc: {
			doctype: 'Insights Chart',
			name: undefined,
			chart_type: undefined,
			options: {},
			is_public: false,
		},
	})

	async function load() {
		state.loading = true
		await resource.get.fetch()
		state.doc = resource.doc
		const _query = useQuery(state.doc.query)
		watchOnce(
			() => _query.doc,
			() => {
				if (!_query.doc) return
				state.data = getFormattedResult(_query.doc.results)
				if (!state.doc.chart_type) state.doc.options = guessChart(state.data)
				state.loading = false
			}
		)
	}
	load()

	function save() {
		resource.setValue
			.submit({
				chart_type: state.doc.chart_type,
				options: state.doc.options,
			})
			.then(() => $notify({ title: 'Chart Saved' }))
	}

	function togglePublicAccess(isPublic) {
		if (state.doc.is_public === isPublic) return
		resource.setValue.submit({ is_public: isPublic }).then(() => {
			$notify({
				title: 'Chart access updated',
				appearance: 'success',
			})
			state.doc.is_public = isPublic
		})
	}

	return Object.assign(state, {
		load,
		save,
		togglePublicAccess,
	})
}

function getChartResource(chartName) {
	return createDocumentResource({
		doctype: 'Insights Chart',
		name: chartName,
		transform: (doc) => {
			doc.options = safeJSONParse(doc.options)
			return doc
		},
	})
}
