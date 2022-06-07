<template>
	<div v-if="query">
		<header class="flex flex-col">
			<!-- Height 5 rem -->
			<div class="flex h-[5rem] justify-between pt-3">
				<div class="relative flex flex-col items-start space-y-1">
					<input
						type="text"
						v-model="query.title"
						ref="title_input"
						spellcheck="false"
						@blur="on_title_update"
						:size="Math.max(query.title.length, 4)"
						@keydown.enter="on_title_update"
						class="peer -mx-2 -my-1 rounded border-none bg-transparent p-0 px-2 py-1 text-3xl font-bold caret-black focus:border-none focus:bg-gray-100/75 focus:outline-none focus:ring-transparent"
					/>
					<div class="flex space-x-2 text-sm font-light text-gray-600">
						<div v-if="data_source" class="flex items-center">
							<FeatherIcon name="database" class="mr-1 h-3 w-3" />
							<span> {{ data_source }} </span>
						</div>
						<div v-if="tables" class="flex items-center">
							<FeatherIcon name="layout" class="mr-1 h-3 w-3" />
							<span> {{ tables }} </span>
						</div>
						<div v-if="last_updated" class="flex items-center">
							<FeatherIcon name="clock" class="mr-1 h-3 w-3" />
							<span> Modified {{ last_updated }} </span>
						</div>
						<div v-if="execution_time" class="flex items-center">
							<FeatherIcon name="clock" class="mr-1 h-3 w-3" />
							<span> {{ last_execution }} executed in {{ execution_time }} sec </span>
						</div>
					</div>
				</div>
				<div class="flex space-x-2">
					<Button
						class="h-fit !shadow"
						:appearance="can_execute ? 'primary' : 'white'"
						@click="$resources.query.run.submit()"
						:loading="$resources.query.run.loading"
					>
						Execute
					</Button>
					<QueryMenu :query="query" />
				</div>
			</div>
			<!-- Height 2.5rem -->
			<TabSwitcher :tabs="tabs" @tab_switched="(tab) => (active_tab = tab)" />
		</header>
		<!-- 100% - 7.5rem (header) + 1rem (margin-top) -->
		<main class="mt-4 flex h-[calc(100%-8.5rem)] w-full rounded-md border bg-white shadow">
			<QueryBuilder v-show="active_tab == 'Build'" :query="$resources.query" />
			<QueryResult v-show="active_tab == 'Result'" :query="$resources.query" />
			<QueryTransform v-show="active_tab == 'Transform'" :query="$resources.query" />
			<QueryChart v-if="active_tab == 'Visualize'" :query="$resources.query" />
		</main>
	</div>
</template>

<script>
import moment from 'moment'
import TabSwitcher from '@/components/TabSwitcher.vue'
import QueryBuilder from '@/components/Query/QueryBuilder.vue'
import QueryResult from '@/components/Query/QueryResult.vue'
import QueryTransform from '@/components/Query/QueryTransform.vue'
import QueryChart from '@/components/Query/QueryChart.vue'
import QueryMenu from '@/components/Query/QueryMenu.vue'

export default {
	name: 'Query',
	props: ['query_id'],
	components: {
		TabSwitcher,
		QueryBuilder,
		QueryResult,
		QueryTransform,
		QueryChart,
		QueryMenu,
	},
	data() {
		return {
			active_tab: 'Build',
			tabs: ['Build', 'Result', 'Transform', 'Visualize'],
		}
	},
	resources: {
		query() {
			return {
				type: 'document',
				doctype: 'Query',
				name: this.query_id,
				whitelistedMethods: {
					run: 'run',
					set_limit: 'set_limit',
					add_table: 'add_table',
					add_column: 'add_column',
					move_column: 'move_column',
					remove_table: 'remove_table',
					update_column: 'update_column',
					remove_column: 'remove_column',
					update_filters: 'update_filters',
					apply_transform: 'apply_transform',
					get_column_values: 'get_column_values',
					get_selectable_tables: 'get_selectable_tables',
					get_selectable_columns: 'get_selectable_columns',
				},
				onError: () => {
					this.$notify({
						title: 'Something went wrong',
						appearance: 'error',
					})
				},
			}
		},
	},
	computed: {
		query() {
			return this.$resources.query.doc
		},
		data_source() {
			return this.query.data_source
		},
		tables() {
			return this.query.tables.map((t) => t.label).join(', ')
		},
		last_updated() {
			return moment(this.query.modified).fromNow()
		},
		execution_time() {
			return this.query.execution_time
		},
		last_execution() {
			return moment(this.query.last_execution).fromNow()
		},
		can_execute() {
			// difference between last_execution and last_updated is less than 0.5 sec
			return Math.abs(moment(this.query.last_execution).diff(moment(this.query.modified), 'seconds')) > 0.5
		},
	},
	methods: {
		on_title_update() {
			if (!this.query.title || this.query.title.length == 0) {
				this.query.title = 'Untitled Query'
			}

			this.$resources.query.setValueDebounced.submit(
				{ title: this.query.title },
				{
					onSuccess: () => {
						this.$notify({
							title: 'Query title updated',
							appearance: 'success',
						})
					},
					onError: () => {
						this.$notify({
							title: 'Something went wrong',
							appearance: 'error',
						})
					},
				}
			)

			this.$refs.title_input.blur()
		},
	},
}
</script>
