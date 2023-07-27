import dayjs from '@/utils/dayjs'
import { call, createResource } from 'frappe-ui'
import { defineStore } from 'pinia'

const sources = createResource({
	url: 'insights.api.get_data_sources',
	initialData: [],
	cache: 'sourceList',
	transform(data) {
		return data.map((source) => {
			source.created_from_now = dayjs(source.creation).fromNow()
			source.title =
				source.is_site_db && source.title == 'Site DB'
					? window.location.hostname
					: source.title
			return source
		})
	},
})

export default defineStore('sources', {
	state: () => ({
		list: [],
		loading: false,
		creating: false,
		deleting: false,
		testing: false,
	}),
	actions: {
		async reload() {
			this.loading = true
			this.list = await sources.fetch()
			this.loading = false
		},
		async testConnection(args) {
			this.testing = true
			const status = call('insights.api.setup.test_database_connection', args)
			this.testing = false
			return status
		},
		async createDatabase(args) {
			this.creating = true
			await call('insights.api.setup.add_database', args)
			this.creating = false
			this.reload()
		},
	},
})
