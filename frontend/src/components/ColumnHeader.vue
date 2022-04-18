<template>
	<div class="group flex items-center justify-between">
		<div>
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
		remove_column(column) {
			this.query.remove_column.submit({ column: column })
		},
	},
}
</script>
