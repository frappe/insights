import { safeJSONParse } from '@/utils'
import { createDocumentResource, createResource } from 'frappe-ui'
import { defineStore } from 'pinia'

const queries = createResource({
	url: 'insights.api.get_queries',
	initialData: [],
	cache: 'queriesList',
})

export default defineStore('queries', {
	state: () => ({
		list: [],
		loading: false,
		creating: false,
		deleting: false,
		currentQuery: undefined,
	}),
	actions: {
		async reload() {
			this.loading = true
			this.list = await queries.fetch()
			this.loading = false
		},
	},
})

export function useQuery(name) {
	const query = createDocumentResource({
		doctype: 'Insights Query',
		name: name,
		transform(doc) {
			doc.columns = doc.columns.map((c) => {
				c.format_option = safeJSONParse(c.format_option, {})
				return c
			})
			doc.results = safeJSONParse(doc.results, [])
			query.resultColumns = doc.results[0].map((c) => {
				return {
					column: c.split('::')[0],
					type: c.split('::')[1],
				}
			})
			return doc
		},
	})
	query.get.fetch()
	return query
}
