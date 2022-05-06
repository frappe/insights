<template>
	<div class="flex flex-col">
		<header class="mx-auto flex w-full max-w-7xl flex-col px-4 sm:px-6 lg:px-8">
			<div class="my-4 flex h-12 items-center justify-between">
				<h1 class="text-3xl font-bold text-gray-900">Queries</h1>
				<div>
					<Button appearance="primary" @click="create_new_query_dialog = true"> + Add Query </Button>
				</div>
			</div>
			<div class="w-full border-b"></div>
		</header>
		<main class="flex h-[calc(100%-5.5rem)] flex-1">
			<div class="mx-auto flex max-w-7xl flex-1 flex-col space-y-4 py-4 sm:px-6 lg:px-8">
				<div class="flex space-x-4">
					<Input type="text" placeholder="Title" />
					<Input type="text" placeholder="Data Source" />
				</div>
				<div class="flex flex-1 flex-col rounded-md border">
					<ul role="list" class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll">
						<li
							class="relative flex cursor-pointer items-center justify-between rounded-md py-3 px-4 text-sm text-gray-500 hover:bg-gray-50"
						>
							<p class="mr-4"><Input type="checkbox" class="rounded-md border-gray-400" /></p>
							<p class="flex-1">Title</p>
							<p class="flex-1">Tables</p>
							<p class="flex-1">Data Source</p>
							<p class="flex-1 text-right">Last Modified</p>
						</li>
						<li v-for="query in queries" :key="query.name">
							<router-link
								:to="{ name: 'Query', params: { query_id: query.name } }"
								class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50"
							>
								<p class="mr-4"><Input type="checkbox" class="rounded-md border-gray-400" /></p>
								<p class="flex-1 whitespace-nowrap text-sm font-medium text-gray-900">{{ query.title }}</p>
								<p class="flex-1 whitespace-nowrap text-sm text-gray-500">{{ query.tables.replace(/,/g, ', ') }}</p>
								<p class="flex-1 whitespace-nowrap text-sm text-gray-500">{{ query.data_source }}</p>
								<p class="flex-1 text-right text-sm text-gray-500" :title="query.modified">
									{{ query.modified_from_now }}
								</p>
							</router-link>
						</li>
					</ul>
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">Showing {{ queries.length }} of {{ queries.length }}</p>
					</div>
				</div>
			</div>
		</main>
		<Dialog :options="{ title: 'New Query' }" v-model="create_new_query_dialog">
			<template #body-content>
				<div class="space-y-4">
					<Input type="select" label="Data Source" v-model="new_query.data_source" :options="data_sources" />
					<Input type="text" label="Title" v-model="new_query.title" />
				</div>
			</template>
			<template #actions>
				<Button appearance="primary" @click="submit_query" :loading="$resources.create_query.loading"> Create </Button>
			</template>
		</Dialog>
	</div>
</template>

<script>
import moment from 'moment'
import { Dialog, Button, Input } from 'frappe-ui'

export default {
	name: 'QueryList',
	components: {
		Button,
		Dialog,
		Input,
	},
	data() {
		return {
			create_new_query_dialog: false,
			new_query: {
				title: '',
				data_source: '',
			},
		}
	},
	resources: {
		get_queries: {
			method: 'analytics.api.get_queries',
			auto: true,
		},
		get_data_sources: {
			method: 'analytics.api.get_data_sources',
			auto: true,
			onSuccess(data_sources) {
				this.new_query.data_source = data_sources[0]
			},
		},
		create_query: {
			method: 'analytics.api.create_query',
			onSuccess(query_name) {
				this.new_query.title = ''
				this.new_query.data_source = ''
				this.create_new_query_dialog = false
				this.$router.push(`/query/${query_name}`)
			},
		},
	},
	computed: {
		queries() {
			const queries = this.$resources.get_queries.data || []
			queries.forEach((query) => {
				query.modified_from_now = moment(query.modified).fromNow()
			})
			return queries
		},
		data_sources() {
			return this.$resources.get_data_sources.data || []
		},
	},
	methods: {
		submit_query() {
			if (this.new_query.title && this.new_query.data_source) {
				this.$resources.create_query.submit({
					title: this.new_query.title,
					data_source: this.new_query.data_source,
				})
			}
		},
	},
}
</script>
