<template>
	<div class="relative" v-on-outside-click="() => (is_open = false)">
		<Popover :show="is_open">
			<template #target>
				<div
					class="mx-1 cursor-pointer rounded border border-transparent px-0.5 py-0.5 text-gray-500 hover:border-gray-200 hover:bg-gray-100 hover:text-gray-600"
					@click="is_open = !is_open"
				>
					<FeatherIcon name="more-vertical" class="h-4 w-4" />
				</div>
			</template>
			<template #content>
				<div class="mt-1 origin-top-right rounded-md bg-white text-base shadow-md ring-1 ring-gray-200">
					<div
						v-for="(item, idx) in menu_items"
						:key="idx"
						class="cursor-pointer px-3 py-1"
						:class="{
							'cursor-default bg-gray-50 text-xs font-light text-gray-500': item.is_header,
							'border-t border-gray-200 text-red-400 hover:underline': item.is_danger_action,
							'text-gray-600 hover:underline': !item.is_header && !item.is_danger_action,
							'text-blue-400':
								(column.aggregation && column.aggregation === item.label) ||
								(column.order_by && column.order_by === item.value),
						}"
						@click="on_menu_item_select(item)"
					>
						{{ item.label }}
					</div>
				</div>
			</template>
		</Popover>
	</div>
</template>

<script>
export default {
	name: 'ColumnMenu',
	props: ['query', 'column'],
	data() {
		return {
			is_open: false,
		}
	},
	resources: {
		aggregations() {
			return {
				method: 'analytics.api.get_aggregation_list',
				auto: true,
				debounce: 300,
			}
		},
	},
	computed: {
		aggregations() {
			return this.$resources.aggregations.data
		},
		menu_items() {
			const remove = { label: 'Remove', for_removing: true, is_danger_action: true }
			const aggregation_items = this.get_aggregation_items()
			const ordering_items = this.get_ordering_items()
			return [...aggregation_items, ...ordering_items, remove]
		},
	},
	methods: {
		on_menu_item_select(item) {
			if (item.is_header) {
				return
			} else if (item.for_aggregating) {
				this.column.aggregation = this.column.aggregation == item.label ? null : item.label
				this.query.update_column.submit({ column: this.column })
			} else if (item.for_ordering) {
				this.column.order_by = this.column.order_by == item.value ? null : item.value
				this.query.update_column.submit({ column: this.column })
			} else if (item.for_removing) {
				this.query.remove_column.submit({ column: this.column })
			}
			this.is_open = false
		},
		get_aggregation_items() {
			if (!this.aggregations?.length) {
				return []
			}
			const agg_header = { label: 'Aggregations', is_header: true }
			const group_by = { label: 'Group By', for_aggregating: true }
			const aggregations = this.aggregations.map((label) => ({
				label,
				for_aggregating: true,
			}))
			return [agg_header, group_by, ...aggregations]
		},
		get_ordering_items() {
			const ordering_header = { label: 'Ordering', is_header: true }
			const asc = { label: 'Ascending', value: 'asc', for_ordering: true }
			const desc = { label: 'Descending', value: 'desc', for_ordering: true }
			return [ordering_header, asc, desc]
		},
	},
}
</script>
