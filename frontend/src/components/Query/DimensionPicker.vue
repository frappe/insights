<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				v-model="_column"
				:options="filtered_columns"
				placeholder="Select a column..."
				@selectOption="on_column_select"
			/>
		</div>
		<div v-if="show_format_options" class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Format</div>
			<Autocomplete
				v-model="format"
				:options="format_options"
				placeholder="Select a format..."
				@selectOption="on_format_select"
			/>
		</div>
		<div v-if="label" class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Label</div>
			<Input type="text" v-model="label" class="h-8 placeholder:text-sm" placeholder="Enter a label..." />
		</div>
		<div class="flex justify-end space-x-2">
			<Button
				v-if="column?.name"
				class="text-red-500"
				appearance="white"
				@click="query.remove_column.submit({ column })"
			>
				Remove
			</Button>
			<Button @click="add_dimension" appearance="primary" :disabled="add_disabled">
				{{ column ? 'Edit' : 'Add ' }}
			</Button>
		</div>
	</div>
</template>

<script>
import { isEmptyObj } from '@/utils/utils.js'
import Autocomplete from '@/components/Autocomplete.vue'

export default {
	name: 'DimensionPicker',
	components: {
		Autocomplete,
	},
	props: ['query', 'column'],
	data() {
		return {
			_column: this.column || {},
			label: this.column?.label || '',
			format: this.column?.format
				? {
						label: this.column.format,
						value: this.column.format,
				  }
				: {},
		}
	},
	mounted() {
		this.query.get_all_columns.fetch()
	},
	computed: {
		add_disabled() {
			return isEmptyObj(this._column) || !this.label
		},
		column_options() {
			const column_list = this.query.get_all_columns?.data?.message || []
			return column_list.map((c) => {
				return {
					...c,
					value: c.column,
					secondary_label: c.table_label,
				}
			})
		},
		filtered_columns() {
			// return all columns except numeric columns
			return this.column_options.filter((c) => !['Int', 'Decimal', 'Bigint', 'Float', 'Double'].includes(c.type))
		},
		show_format_options() {
			return !isEmptyObj(this._column) && ['Datetime', 'Timestamp', 'Date'].includes(this._column.type)
		},
		format_options() {
			if (!this.show_format_options) return []

			let format_options = []

			if (['Datetime', 'Timestamp'].includes(this._column.type)) {
				format_options = [
					'Minute',
					'Hour',
					'Day',
					'Month',
					'Year',
					'Minute of Hour',
					'Hour of Day',
					'Day of Week',
					'Day of Month',
					'Day of Year',
					'Month of Year',
					'Quarter of Year',
				]
			}

			if (this._column.type == 'Date') {
				format_options = [
					'Day',
					'Month',
					'Year',
					'Day of Week',
					'Day of Month',
					'Day of Year',
					'Month of Year',
					'Quarter of Year',
				]
			}

			return format_options.map((f) => {
				return {
					label: f,
					value: f,
				}
			})
		},
	},
	methods: {
		on_column_select(option) {
			this._column = option ? option : {}
			this.label = !this.label && this._column.label ? this._column.label : this.label
		},
		on_format_select(option) {
			this.format = option ? option : {}
		},
		add_dimension() {
			if (isEmptyObj(this._column)) {
				return
			}

			this._column.label = this.label
			this._column.aggregation = 'Group By'
			this._column.format = this.format.value
			this.$emit('column-select', this._column)
		},
	},
}
</script>
