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
							'cursor-default border-b border-gray-200 text-xs font-light text-gray-500': item.is_header,
							'border-t border-gray-200 text-red-400 hover:bg-gray-50': item.is_danger_action,
							'text-gray-600 hover:bg-gray-50': item.is_aggregation,
							'bg-blue-50 text-blue-400 hover:bg-blue-50': column.aggregation == item.label,
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
			const remove = { label: 'Remove', is_danger_action: true }
			const agg_header = { label: 'Aggregations', is_header: true }
			if (this.aggregations?.length) {
				const group_by = { label: 'Group By', is_aggregation: true }
				const aggregations = this.aggregations.map((label) => ({
					label,
					is_aggregation: true,
				}))
				return [agg_header, group_by, ...aggregations, remove]
			} else {
				return [remove]
			}
		},
	},
	methods: {
		on_menu_item_select(agg) {
			if (agg.is_header) {
				return
			} else if (agg.is_aggregation) {
				this.column.aggregation = this.column.aggregation == agg.label ? null : agg.label
				this.query.update_column.submit({ column: this.column })
			} else if (agg.is_danger_action) {
				this.query.remove_column.submit({ column: this.column })
			}
			this.is_open = false
		},
	},
}
</script>
