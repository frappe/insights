import dayjs from '@/utils/dayjs'
import { call, createResource } from 'frappe-ui'
import { defineStore } from 'pinia'

const queries = createResource({
	url: 'insights.api.get_queries',
	initialData: [],
	cache: 'queriesList',
	transform(data) {
		return data.map((qry) => {
			qry.created_from_now = dayjs(qry.creation).fromNow()
			return qry
		})
	},
})

export default defineStore('queries', {
	state: () => ({
		list: [],
		loading: false,
		creating: false,
		deleting: false,
	}),
	actions: {
		async reload() {
			this.loading = true
			this.list = await queries.fetch()
			this.loading = false
		},
		async create(query) {
			this.creating = true
			const queryDoc = await call('insights.api.create_query', query)
			await this.reload()
			this.creating = false
			return queryDoc
		},
		async get(name) {
			if (!name) return
			const existingQuery = this.list.find((q) => q.name === name)
			if (existingQuery) return existingQuery
			await this.reload()
			return this.list.find((q) => q.name === name)
		},
		async delete(name) {
			this.deleting = true
			await call('frappe.client.delete', { doctype: 'Insights Query', name })
			await this.reload()
			this.deleting = false
		},
	},
})
