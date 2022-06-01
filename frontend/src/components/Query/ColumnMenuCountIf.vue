<template>
	<Popover :show="is_open" placement="right-start">
		<template #target>
			<span
				class="column-menu-item-popover flex items-center"
				:class="{
					'-my-1 -mx-2 rounded-md bg-gray-100 py-1 px-2 text-gray-800': is_open,
				}"
				@click="is_open = !is_open"
			>
				{{ menu_item.label }}
			</span>
		</template>
		<template #content>
			<div class="column-menu-item-popover-content mx-5 w-[28rem] rounded-md bg-white shadow-md ring-1 ring-gray-200">
				<SimpleFilterPicker :query="query" :conditions="conditions" @select="apply_condition" />
			</div>
		</template>
	</Popover>
</template>

<script>
import SimpleFilterPicker from '@/components/SimpleFilterPicker.vue'
export default {
	name: 'ColumnMenuCountIf',
	components: { SimpleFilterPicker },
	props: ['query', 'menu_item', 'column'],
	data() {
		return {
			is_open: false,
		}
	},
	computed: {
		conditions() {
			if (this.column.aggregation == 'Count if') {
				const aggregation_conditions = JSON.parse(this.column.aggregation_condition)
				return aggregation_conditions.map((condition) => {
					return {
						left: {
							value: condition.left.column,
						},
						operator: {
							value: condition.operator.value,
						},
						right: {
							value: condition.right.value,
						},
					}
				})
			}
			return []
		},
	},
	mounted() {
		this.outside_click_listener = (e) => {
			if (e.target.closest('.column-menu-item-popover') || e.target.closest('.column-menu-item-popover-content')) {
				return
			}
			this.is_open = false
		}
		document.addEventListener('click', this.outside_click_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
	methods: {
		apply_condition(conditions) {
			this.is_open = false
			if (conditions && conditions.length) {
				this.column.aggregation = this.menu_item.value
				this.column.aggregation_condition = JSON.stringify(conditions, null, 2)
				this.query.update_column.submit({ column: this.column })
				this.$emit('apply')
			}
		},
	},
}
</script>
