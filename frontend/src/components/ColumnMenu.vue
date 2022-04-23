<template>
	<div class="relative" v-on-outside-click="() => (is_open = false)">
		<Popover :show="is_open">
			<template #target>
				<div
					class="cursor-pointer rounded border border-transparent px-0.5 py-0.5 text-gray-500 hover:border-gray-200 hover:bg-gray-100 hover:text-gray-600"
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
								(column.aggregation && column.aggregation === item.value) ||
								(column.format && column.format === item.value),
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
		column_menu_options() {
			return {
				method: 'analytics.api.get_column_menu_options',
				params: { fieldtype: this.column.type },
				auto: true,
				debounce: 300,
			}
		},
	},
	computed: {
		format_options() {
			return this.$resources.column_menu_options.data?.format_options
		},
		aggregation_options() {
			return this.$resources.column_menu_options.data?.aggregation_options
		},
		menu_items() {
			const remove = { label: 'Remove', for_removing: true, is_danger_action: true }
			const format_items = this.get_format_items()
			const aggregation_items = this.get_aggregation_items()
			return [...aggregation_items, ...format_items, remove]
		},
	},
	methods: {
		on_menu_item_select(item) {
			if (item.is_header) {
				return
			} else if (item.for_aggregation) {
				this.column.aggregation = this.column.aggregation == item.value ? null : item.value
				this.query.update_column.submit({ column: this.column })
			} else if (item.for_formatting) {
				this.column.format = this.column.format == item.value ? null : item.value
				this.query.update_column.submit({ column: this.column })
			} else if (item.for_removing) {
				this.query.remove_column.submit({ column: this.column })
			}
			this.is_open = false
		},
		get_aggregation_items() {
			if (!this.aggregation_options?.length) {
				return []
			}
			const agg_header = { label: 'Aggregations', is_header: true }
			const aggregations = this.aggregation_options.map((label) => ({
				...label,
				for_aggregation: true,
			}))
			return [agg_header, ...aggregations]
		},
		get_format_items() {
			if (!this.format_options?.length) {
				return []
			}
			const format_header = { label: 'Column Formatting', is_header: true }
			const formatting_items = this.format_options.map((label) => ({
				...label,
				for_formatting: true,
			}))
			return [format_header, ...formatting_items]
		},
	},
}
</script>
