<template>
	<div class="flex flex-1 flex-col py-10">
		<header>
			<div
				class="mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8"
			>
				<h1 class="text-3xl font-bold leading-tight text-gray-900">
					All Queries
				</h1>
				<div class="">
					<Button appearance="primary" @click="create_new_query_dialog = true">
						+ Add Query
					</Button>
				</div>
			</div>
		</header>
		<main class="flex flex-1">
			<div class="mx-auto flex max-w-7xl flex-1 py-8 sm:px-6 lg:px-8">
				<div class="flex-1 rounded-md bg-white p-4 shadow">
					<ul role="list" class="divide-y divide-gray-200">
						<li
							v-for="query in queries"
							:key="query.id"
							class="flex cursor-pointer items-center justify-between rounded-md px-2 py-2 hover:bg-gray-50"
							@click="$router.push(`/query/${query.id}`)"
						>
							<div class="ml-3">
								<p class="text-sm font-medium text-gray-900">
									{{ query.title }}
								</p>
								<p class="text-sm text-gray-500">
									{{ query.tables.join(', ') }}
								</p>
							</div>
							<FeatherIcon
								name="chevron-right"
								class="h-5 w-5 text-gray-500"
								aria-hidden="true"
							/>
						</li>
					</ul>
				</div>
			</div>
		</main>
		<Dialog :options="{ title: 'New Query' }" v-model="create_new_query_dialog">
			<template #body-content>
				<Input
					type="text"
					label="Title"
					v-model="new_query_title"
					@keydown.enter="submit_query"
				/>
				<ErrorMessage class="mt-2" :message="$resources.create_query.error" />
			</template>
			<template #actions>
				<Button
					appearance="primary"
					@click="submit_query"
					:loading="$resources.create_query.loading"
				>
					Create
				</Button>
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
			new_query_title: '',
			queries: [
				{
					title: 'First Query',
					id: 'First Query',
					tables: ['ToDo', 'Comment'],
				},
			],
		}
	},
	resources: {
		create_query: {
			method: 'frappe.client.insert',
			onSuccess(query) {
				this.new_query_title = ''
				this.create_new_query_dialog = false
				this.$router.push(`/query/${query.name}`)
			},
		},
	},
	methods: {
		submit_query() {
			if (this.new_query_title) {
				this.$resources.create_query.submit({
					doc: {
						doctype: 'Query',
						title: this.new_query_title,
					},
				})
			}
		},
	},
}
</script>
