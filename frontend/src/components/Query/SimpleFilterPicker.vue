<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				id="column"
				:options="column_list"
				v-model="column"
				placeholder="Select a column..."
				@option-select="on_column_select"
			/>
		</div>
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Operator</div>
			<Autocomplete
				id="operator"
				:options="operator_list"
				v-model="operator"
				placeholder="Select operator..."
				@option-select="on_operator_select"
			/>
		</div>
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Value</div>
			<Autocomplete
				id="value"
				v-model="value"
				:options="value_list"
				:placeholder="value_placeholder"
				@option-select="on_value_select"
			/>
		</div>
		<div class="flex justify-end">
			<Button appearance="primary" :disabled="!column || !operator || !value" @click="apply"> Apply </Button>
		</div>
	</div>
</template>

<script>
import Autocomplete from '@/components/Autocomplete.vue'
import { debounce } from 'frappe-ui'

export default {
	name: 'SimpleFilterPicker',
	props: ['query', 'filter'],
	components: {
		Autocomplete,
	},
	data() {
		return {
			column: this.filter?.left?.label || '',
			operator: this.filter?.operator?.label || '',
			value: this.filter?.right?.label || '',
			_filter: this.filter || {
				left: '',
				operator: '',
				right: '',
			},
		}
	},
	resources: {
		operator_list() {
			return {
				method: 'analytics.api.get_operator_list',
			}
		},
	},
	mounted() {
		this.query.get_selectable_columns.fetch()
	},
	computed: {
		column_list() {
			// Column: { label, table, table_label, column, type }
			return this.query.get_selectable_columns?.data?.message || []
		},
		operator_list() {
			// Operator: { label, value }
			return this.$resources.operator_list.data || []
		},
		value_list() {
			if (
				!this._filter.left?.column ||
				!this._filter.operator?.value ||
				!['=', '!=', 'is'].includes(this._filter.operator.value)
			) {
				return []
			}
			if (this._filter.operator.value == 'is') {
				return [
					{ label: 'Set', value: 'set' },
					{ label: 'Not Set', value: 'not set' },
				]
			}
			return this.query.get_column_values?.data?.message || []
		},
		value_placeholder() {
			if (!this._filter.operator?.value) {
				return 'Type a value...'
			}
			if (this._filter.operator.value.includes('in')) {
				return 'Type comma separated values...'
			}
			if (this._filter.operator.value.includes('between')) {
				return 'Type two comma separated values...'
			}
			return 'Type a value...'
		},
	},
	watch: {
		value(new_value) {
			this.check_and_fetch_column_values()
			if (!this.value_list.length) {
				this._filter.right = {
					value: new_value,
					label: new_value,
				}
			}
		},
	},
	methods: {
		on_column_select(option) {
			this._filter.left = option
			this._filter.operator = {}
			this._filter.right = {}
			this.operator = ''
			this.value = ''
			this.$resources.operator_list.submit({
				fieldtype: this._filter.left.type,
			})
		},
		on_operator_select(option) {
			this._filter.operator = option
			this._filter.right = {}
			this.value = ''
		},
		on_value_select(option) {
			this._filter.right = option
		},
		apply() {
			if (!this.column || !this.operator || !this.value) {
				return
			}
			this.$emit('filter-select', { filter: this._filter })
		},
		check_and_fetch_column_values: debounce(function () {
			if (
				!this.value ||
				!this._filter.left?.column ||
				!this._filter.operator?.value ||
				!['=', '!='].includes(this._filter.operator.value)
			) {
				return
			}

			const left_is_smalltext = ['varchar', 'char', 'enum'].includes(this._filter.left.type.toLowerCase())
			if (left_is_smalltext) {
				this.query.get_column_values.submit({
					column: this._filter.left,
					search_text: this.value,
				})
			}
		}, 300),
	},
}
</script>
