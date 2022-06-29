<template>
	<div class="column-menu relative">
		<Popover :show="show" class="flex w-full [&>div:first-child]:w-full">
			<template #target="{ togglePopover }">
				<div
					class="cursor-pointer rounded px-1 py-0.5 text-gray-500 hover:text-gray-600"
					@click="
						() => {
							show = true
							togglePopover()
						}
					"
				>
					<FeatherIcon name="more-vertical" class="h-4 w-4" />
				</div>
			</template>
			<template #body>
				<div
					v-if="show"
					class="column-menu-popover mt-1 origin-top-right rounded-md bg-white p-1 text-base shadow-md ring-1 ring-gray-200"
				>
					<div
						v-for="(item, idx) in menu_items"
						:key="idx"
						class="cursor-pointer select-none px-3 py-1"
						:class="{
							'cursor-default bg-gray-50 text-xs font-light text-gray-500 first:rounded-t-md':
								item.is_header,
							'border-t border-gray-200 text-red-400 hover:rounded-md hover:bg-gray-100':
								item.is_danger_action,
							'text-gray-600 hover:rounded-md hover:bg-gray-100':
								!item.is_header && !item.is_danger_action,
							'text-blue-400':
								(column.aggregation && column.aggregation === item.value) ||
								(column.format && column.format === item.value),
						}"
						@click="on_menu_item_select(item)"
					>
						<div v-if="item.has_popover">
							<ColumnMenuCountIf
								v-if="item.label == 'Count if'"
								:query="query"
								:menu_item="item"
								:column="column"
								@apply="show = false"
							/>
						</div>
						<div v-else>{{ item.label }}</div>
					</div>
				</div>
			</template>
		</Popover>
	</div>
</template>

<script>
import ColumnMenuCountIf from '@/components/Query/ColumnMenuCountIf.vue'

export default {
	name: 'ColumnMenu',
	components: { ColumnMenuCountIf },
	props: ['query', 'column'],
	data() {
		return {
			show: false,
		}
	},
	mounted() {
		this.outside_click_listener = (e) => {
			if (
				e.target.closest('.column-menu') ||
				e.target.closest('.column-menu-popover') ||
				e.target.closest('.column-menu-item-popover') ||
				e.target.closest('.column-menu-item-popover-content')
			) {
				return
			}
			this.show = false
		}
		document.addEventListener('click', this.outside_click_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
	resources: {
		column_menu_options() {
			return {
				method: 'insights.api.get_column_menu_options',
				params: { fieldtype: this.column.type },
				debounce: 300,
				auto: true,
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
			if (item.is_header || item.has_popover) {
				return
			} else if (item.for_aggregation) {
				this.column.aggregation = this.column.aggregation == item.value ? null : item.value
				this.query.updateColumn.submit({ column: this.column })
			} else if (item.for_formatting) {
				this.column.format = this.column.format == item.value ? null : item.value
				this.query.updateColumn.submit({ column: this.column })
			} else if (item.for_removing) {
				this.query.removeColumn.submit({ column: this.column })
			}
			this.show = false
		},
		get_aggregation_items() {
			if (!this.aggregation_options?.length) {
				return []
			}
			const agg_header = { label: 'Aggregations', is_header: true }
			const aggregations = this.aggregation_options.map((option) => ({
				...option,
				for_aggregation: true,
				has_popover: option.label === 'Count if',
			}))
			return [agg_header, ...aggregations]
		},
		get_format_items() {
			if (!this.format_options?.length) {
				return []
			}
			const format_header = { label: 'Column Formatting', is_header: true }
			const formatting_items = this.format_options.map((option) => ({
				...option,
				for_formatting: true,
			}))
			return [format_header, ...formatting_items]
		},
	},
}
</script>
