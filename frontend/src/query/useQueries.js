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
		filterByText(text) {
			if (!text) return this.list
			return this.list.filter((q) => {
				return (
					q.title.toLowerCase().includes(text.toLowerCase()) ||
					q.name.toLowerCase().includes(text.toLowerCase()) ||
					q.data_source.toLowerCase().includes(text.toLowerCase())
				)
			})
		},
	},
})
