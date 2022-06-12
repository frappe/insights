<template>
	<Popover placement="right-start" class="flex w-full [&>div:first-child]:w-full">
		<template #target="{ isOpen, togglePopover }">
			<span
				class="column-menu-item-popover flex items-center"
				:class="{
					'-my-1 -mx-2 rounded-md bg-gray-100 py-1 px-2 text-gray-800': isOpen,
				}"
				@click="togglePopover"
			>
				{{ menu_item.label }}
			</span>
		</template>
		<template #body="{ togglePopover }">
			<div class="column-menu-item-popover-content mx-5 w-[28rem] rounded-md bg-white shadow-md ring-1 ring-gray-200">
				<SimpleFilterPicker
					:query="query"
					:conditions="conditions"
					@select="
						(conditions) => {
							apply_condition(conditions)
							togglePopover()
						}
					"
				/>
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
	methods: {
		apply_condition(conditions) {
			if (conditions && conditions.length) {
				this.column.aggregation = this.menu_item.value
				this.column.aggregation_condition = JSON.stringify(conditions, null, 2)
				this.query.updateColumn.submit({ column: this.column })
				this.$emit('apply')
			}
		},
	},
}
</script>
