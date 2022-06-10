<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				id="column"
				v-model="column"
				:options="column_options"
				placeholder="Select a column..."
				@option-select="on_column_select"
			/>
		</div>
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Operator</div>
			<Autocomplete
				id="operator"
				v-model="operator"
				:options="operator_list"
				placeholder="Select operator..."
				@option-select="on_operator_select"
			/>
		</div>
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Value</div>
			<Autocomplete
				v-if="show_value_options"
				id="value"
				v-model="value"
				:options="value_list"
				:placeholder="value_placeholder"
				@option-select="on_value_select"
			/>
			<TimespanPicker
				v-else-if="show_timespan_picker"
				id="value"
				v-model="value"
				@change="on_value_select"
				:placeholder="value_placeholder"
			/>
			<DatePicker
				v-else-if="show_datepicker"
				id="value"
				:value="value.value"
				:placeholder="value_placeholder"
				:formatValue="format_date"
				@change="
					(date) => {
						value.value = date
						on_value_select({
							value: date,
							label: format_date(date),
						})
					}
				"
			/>
			<input
				v-else
				type="text"
				v-model="value.value"
				:placeholder="value_placeholder"
				class="form-input block h-8 w-full select-none rounded-md placeholder-gray-500 placeholder:text-sm"
			/>
		</div>
		<div class="flex justify-end">
			<Button @click="apply" appearance="primary" :disabled="apply_disabled"> Apply </Button>
		</div>
	</div>
</template>

<script>
import Autocomplete from '@/components/Autocomplete.vue'
import TimespanPicker from '@/components/TimespanPicker.vue'
import DatePicker from '@/components/DatePicker.vue'
import { isEmptyObj } from '@/utils/utils.js'
import { debounce } from 'frappe-ui'

export default {
	name: 'SimpleFilterPicker',
	props: ['query', 'filter'],
	components: {
		TimespanPicker,
		Autocomplete,
		DatePicker,
	},
	data() {
		return {
			column: this.filter?.left || {},
			operator: this.filter?.operator || {},
			value: this.filter?.right || {},
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
		if (!isEmptyObj(this._filter.left)) {
			this.$resources.operator_list.submit({
				fieldtype: this._filter.left.type,
			})
		}
	},
	computed: {
		column_list() {
			// Column: { label, table, table_label, column, type }
			return this.query.get_selectable_columns?.data?.message || []
		},
		column_options() {
			return this.column_list.map((c) => {
				return {
					...c,
					value: c.column,
					secondary_label: c.table_label,
				}
			})
		},
		operator_list() {
			// Operator: { label, value }
			return this.$resources.operator_list.data || []
		},
		value_list() {
			if (this._filter.operator.value == 'is') {
				return [
					{ label: 'Set', value: 'set' },
					{ label: 'Not Set', value: 'not set' },
				]
			}
			if (isEmptyObj(this.value) || !this.value.value) {
				return []
			}
			return this.query.get_column_values?.data?.message || []
		},
		value_placeholder() {
			if (this.show_datepicker) {
				return 'Select a date...'
			}
			if (isEmptyObj(this._filter.operator)) {
				return 'Type a value...'
			}
			if (this._filter.operator.value == 'between') {
				return 'Type two comma separated values...'
			}
			if (this._filter.operator.value == 'in' || this._filter.operator.value == 'not in') {
				return 'Type comma separated values...'
			}
			return 'Type a value...'
		},
		show_timespan_picker() {
			return ['Date', 'Datetime'].includes(this._filter.left?.type) && this._filter.operator?.value === 'timespan'
		},
		show_datepicker() {
			return (
				['Date', 'Datetime'].includes(this._filter.left?.type) &&
				['=', '!=', '>', '>=', '<', '<=', 'between'].includes(this._filter.operator?.value)
			)
		},
		show_value_options() {
			if (
				isEmptyObj(this._filter.left) ||
				isEmptyObj(this._filter.operator) ||
				['Date', 'Datetime'].includes(this._filter.left?.type) ||
				!['=', '!=', 'is'].includes(this._filter.operator.value)
			) {
				return false
			}
			return true
		},
		apply_disabled() {
			return isEmptyObj(this.column) || isEmptyObj(this.operator) || isEmptyObj(this.value)
		},
	},
	watch: {
		value: {
			handler(new_value) {
				this.check_and_fetch_column_values()
				if (!this.show_value_options && !this.show_datepicker && !this.show_timespan_picker) {
					this._filter.right = {
						label: new_value.value,
						value: new_value.value,
					}
				}
			},
			deep: true,
		},
	},
	methods: {
		on_column_select(option) {
			this._filter.left = option
			this._filter.operator = {}
			this._filter.right = {}
			this.operator = {}
			this.value = {}
			this.$resources.operator_list.submit({
				fieldtype: this._filter.left.type,
			})
		},

		on_operator_select(option) {
			this._filter.operator = option
			this._filter.right = {}
			this.value = {}
		},

		on_value_select(option) {
			this._filter.right = option
		},

		apply() {
			if (isEmptyObj(this.column) || isEmptyObj(this.operator) || isEmptyObj(this.value)) {
				return
			}
			this.$emit('filter-select', { filter: this._filter })
		},

		check_and_fetch_column_values: debounce(function () {
			if (
				isEmptyObj(this.value) ||
				!this.value.value ||
				isEmptyObj(this._filter.left) ||
				isEmptyObj(this._filter.operator) ||
				!['=', '!='].includes(this._filter.operator.value)
			) {
				return
			}

			const left_is_smalltext = ['varchar', 'char', 'enum'].includes(this._filter.left.type.toLowerCase())
			if (left_is_smalltext) {
				this.query.get_column_values.submit({
					column: this._filter.left,
					search_text: this.value.value || this.value.label,
				})
			}
		}, 300),

		format_date(value) {
			if (!value) {
				return ''
			}
			return new Date(value).toLocaleString('en-US', {
				month: 'short',
				year: 'numeric',
				day: 'numeric',
			})
		},
	},
}
</script>
