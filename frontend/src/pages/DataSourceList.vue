<template>
	<div>
		<header class="flex h-[5rem] items-center justify-between border-b py-4">
			<h1 class="text-3xl font-bold text-gray-900">Data Sources</h1>
			<div>
				<Button appearance="primary" @click="new_dialog = true"> + Add Data Source </Button>
			</div>
		</header>
		<main class="flex h-[calc(100%-5rem)] flex-col space-y-4 py-4">
			<div class="flex space-x-4">
				<Input type="text" placeholder="Status" />
			</div>
			<div class="flex h-[calc(100%-1.75rem)] flex-col rounded-md border">
				<!-- List Header -->
				<div class="flex items-center justify-between border-b py-3 px-4 text-sm text-gray-500">
					<p class="mr-4"><Input type="checkbox" class="rounded-md border-gray-400" /></p>
					<p class="flex-1">Title</p>
					<p class="flex-1">Status</p>
					<p class="flex-1">Username</p>
					<p class="flex-1">Database Type</p>
					<p class="flex-1 text-right">Last Modified</p>
				</div>
				<ul role="list" class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll">
					<li v-for="source in sources" :key="source.name">
						<a class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50">
							<p class="mr-4"><Input type="checkbox" class="rounded-md border-gray-400" /></p>
							<p class="flex-1 whitespace-nowrap text-sm font-medium text-gray-900">
								{{ source.title }}
							</p>
							<p class="flex-1 whitespace-nowrap text-sm text-gray-500">
								<Badge :color="source.status == 'Inactive' ? 'yellow' : 'green'">
									{{ source.status }}
								</Badge>
							</p>
							<p class="flex-1 whitespace-nowrap text-sm text-gray-500">{{ source.username }}</p>
							<p class="flex-1 whitespace-nowrap text-sm text-gray-500">
								{{ source.database_type }}
							</p>
							<p class="flex-1 text-right text-sm text-gray-500" :title="source.modified">
								{{ source.modified_from_now }}
							</p>
						</a>
					</li>
				</ul>
				<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
					<p class="ml-auto">Showing {{ sources.length }} of {{ sources.length }}</p>
				</div>
			</div>
		</main>
		<Dialog :options="{ title: 'New Data Source' }" v-model="new_dialog">
			<template #body-content>
				<div class="text-sm text-gray-400">Not implemented yet</div>
			</template>
		</Dialog>
	</div>
</template>

<script>
import moment from 'moment'
import { Dialog, Button, Input, Badge } from 'frappe-ui'

export default {
	name: 'DataSourceList',
	components: {
		Button,
		Dialog,
		Input,
		Badge,
	},
	data() {
		return {
			new_dialog: false,
		}
	},
	resources: {
		get_data_sources: {
			method: 'insights.api.get_data_sources',
			auto: true,
		},
	},
	computed: {
		sources() {
			const sources = this.$resources.get_data_sources.data || []
			sources.forEach((source) => {
				source.modified_from_now = moment(source.modified).fromNow()
			})
			return sources
		},
	},
}
</script>
