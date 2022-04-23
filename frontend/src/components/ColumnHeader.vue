<template>
	<div class="group flex items-center justify-between">
		<div class="flex items-center">
			<span
				v-if="column.aggregation"
				class="my-0 mr-2 flex-1 select-none whitespace-nowrap rounded border border-orange-200 px-1 py-0.5 text-xs text-orange-400/80"
			>
				{{ column.aggregation }}
			</span>
			<input
				type="text"
				spellcheck="false"
				ref="column_label_input"
				v-model="column.label"
				:size="Math.max(parseInt(column.label?.length * 1.2), 6)"
				class="mr-2 cursor-text border-none bg-transparent p-0 pr-2 text-base focus:border-none focus:text-gray-600 focus:outline-none focus:ring-transparent"
				@blur="query.get.fetch()"
				@keydown.enter="update_column_label(column)"
			/>
		</div>
		<div class="flex select-none items-center justify-end">
			<div
				@click.prevent.stop="order_by_column"
				class="cursor-pointer rounded border border-transparent py-1 text-gray-500 hover:border-gray-200 hover:bg-gray-100 hover:text-gray-600"
			>
				<FeatherIcon v-if="column.order_by == 'asc'" name="arrow-up" class="mx-1 h-3 w-3" />
				<FeatherIcon v-else-if="column.order_by == 'desc'" name="arrow-down" class="mx-1 h-3 w-3" />
				<FeatherIcon v-else name="code" class="mx-1 h-3 w-3 rotate-90" />
			</div>
			<ColumnMenu :query="query" :column="column" />
		</div>
	</div>
</template>

<script>
import ColumnMenu from './ColumnMenu.vue'

export default {
	name: 'ColumnHeader',
	props: ['column', 'query'],
	components: {
		ColumnMenu,
	},
	methods: {
		update_column_label(column) {
			if (!column.label?.length) {
				this.query.get.fetch()
				return
			}
			this.query.update_column.submit({ column: column })
		},
		order_by_column() {
			this.column.order_by = !this.column.order_by ? 'asc' : this.column.order_by == 'asc' ? 'desc' : null
			this.query.update_column.submit({ column: this.column })
		},
	},
}
</script>
