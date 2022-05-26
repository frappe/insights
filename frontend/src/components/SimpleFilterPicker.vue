<template>
	<div class="flex flex-col space-y-3 p-4 text-base text-gray-700">
		<div v-for="(condition, idx) in _conditions" :key="idx" class="flex items-center space-x-2">
			<div class="flex-1">
				<Input type="select" v-model="condition.left.value" :options="column_options" @input="fetch_operators" />
			</div>
			<div class="flex-1">
				<Input class="flex-1" type="select" v-model="condition.operator.value" :options="operator_options" />
			</div>
			<div class="flex-1">
				<Input class="flex-1" type="text" v-model="condition.right.value" />
			</div>
			<FeatherIcon
				name="x"
				class="h-4 w-4 cursor-pointer text-gray-500 hover:text-gray-800"
				@click.stop.prevent="_conditions.splice(idx, 1)"
			/>
		</div>
		<div class="flex space-x-2 self-end">
			<Button appearance="white" @click="add_condition">Add</Button>
			<Button appearance="primary" @click="apply_condition">Done</Button>
		</div>
	</div>
</template>

<script>
import { debounce } from 'frappe-ui'

export default {
	name: 'SimpleFilterPicker',
	props: ['query', 'conditions'],
	data() {
		return {
			_conditions: this.conditions || [
				{
					left: {
						value: '',
					},
					operator: {
						value: '=',
					},
					right: {
						value: '',
					},
				},
			],
		}
	},
	mounted() {
		this.query.get_selectable_columns.submit({})
	},
	resources: {
		operator_list() {
			return {
				method: 'analytics.api.get_operator_list',
				auto: true,
			}
		},
	},
	computed: {
		column_list() {
			// Column: { label, table, table_label, column, type }
			return this.query.get_selectable_columns?.data?.message || []
		},
		column_options() {
			return [''].concat(
				this.column_list.map((column) => ({
					label: column.label,
					value: column.column,
				}))
			)
		},
		operator_options() {
			// Operator: { label, value }
			return this.$resources.operator_list.data || []
		},
	},
	watch: {},
	methods: {
		fetch_operators: debounce(function (column) {
			if (column) {
				const column_type = this.column_list.find((c) => c.column === column).type
				this.$resources.operator_list.submit({
					fieldtype: column_type,
				})
			}
		}, 200),
		add_condition() {
			this._conditions.push({
				left: {
					value: '',
				},
				operator: {
					value: '=',
				},
				right: {
					value: '',
				},
			})
		},
		apply_condition() {
			const conditions = this._conditions
				.filter((c) => c.left.value && c.operator.value && c.right.value)
				.map((condition) => {
					return {
						left: this.column_list.find((c) => c.column === condition.left.value),
						operator: this.operator_options.find((o) => o.value === condition.operator.value),
						right: {
							label: condition.right.value,
							value: condition.right.value,
						},
					}
				})
			this.$emit('select', conditions)
		},
	},
}
</script>
