<template>
	<div class="flex flex-col pt-10">
		<header>
			<div class="mx-auto flex h-12 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
				<h1 class="text-3xl font-bold leading-tight text-gray-900">All Queries</h1>
				<div class="">
					<Button appearance="primary" @click="create_new_query_dialog = true"> + Add Query </Button>
				</div>
			</div>
		</header>
		<main class="flex h-[calc(100%-5.5rem)] flex-1">
			<div class="mx-auto flex max-w-7xl flex-1 py-8 sm:px-6 lg:px-8">
				<ul
					role="list"
					class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll rounded-md bg-white p-4 shadow"
				>
					<li v-for="query in queries" :key="query.name">
						<router-link
							:to="{ name: 'QueryBuilder', params: { query_id: query.name } }"
							class="flex cursor-pointer items-center justify-between rounded-md px-2 py-2 hover:bg-gray-50"
						>
							<div class="ml-3">
								<p class="text-sm font-medium text-gray-900">
									{{ query.title }}
								</p>
								<p class="text-sm text-gray-500">
									{{ query.tables }}
								</p>
							</div>
							<FeatherIcon name="chevron-right" class="h-5 w-5 text-gray-500" aria-hidden="true" />
						</router-link>
					</li>
				</ul>
			</div>
		</main>
		<Dialog :options="{ title: 'New Query' }" v-model="create_new_query_dialog">
			<template #body-content>
				<div class="space-y-4">
					<Input type="select" label="Data Source" v-model="new_query.data_source" :options="data_sources" />
					<Input type="text" label="Title" v-model="new_query.title" @keydown.enter="submit_query" />
				</div>
			</template>
			<template #actions>
				<Button appearance="primary" @click="submit_query" :loading="$resources.create_query.loading"> Create </Button>
			</template>
		</Dialog>
	</div>
</template>

<script>
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
		create_query: {
			method: 'frappe.client.insert',
			onSuccess(query) {
				this.new_query.title = ''
				this.new_query.data_source = ''
				this.create_new_query_dialog = false
				this.$router.push(`/query/${query.name}`)
			},
		},
	},
	computed: {
		queries() {
			return this.$resources.get_queries.data || []
		},
		data_sources() {
			return ['', 'dev-erpnext', 'testsite.one']
		},
	},
	methods: {
		submit_query() {
			if (this.new_query.title && this.new_query.data_source) {
				this.$resources.create_query.submit({
					doc: {
						doctype: 'Query',
						title: this.new_query.title,
						data_source: this.new_query.data_source,
					},
				})
			}
		},
	},
}
</script>
