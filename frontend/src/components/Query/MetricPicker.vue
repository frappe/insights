<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Type</div>
			<Autocomplete
				id="type"
				v-model="type"
				:options="type_options"
				placeholder="Select metric type..."
				@option-select="on_type_select"
			/>
		</div>
		<div v-if="column_needed" class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				id="column"
				v-model="_column"
				:options="filtered_columns"
				placeholder="Select a column..."
				@option-select="on_column_select"
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
			<Button @click="add_metric" appearance="primary" :disabled="add_disabled">
				{{ column ? 'Edit' : 'Add ' }}
			</Button>
		</div>
	</div>
</template>

<script>
import { isEmptyObj } from '@/utils/utils.js'
import Autocomplete from '@/components/Autocomplete.vue'

export default {
	name: 'MetricPicker',
	components: {
		Autocomplete,
	},
	props: ['query', 'column'],
	data() {
		const type_options = [
			{
				label: 'Count of records',
				value: 'Count',
			},
			{
				label: 'Sum of',
				value: 'Sum',
			},
			{
				label: 'Avg of',
				value: 'Avg',
			},
		]
		const type = type_options.find((t) => t.value === this.column?.aggregation)
		return {
			_column: this.column || null,
			label: this.column?.label || '',
			type_options,
			type,
		}
	},
	mounted() {
		this.query.get_selectable_columns.fetch()
	},
	computed: {
		add_disabled() {
			return !this.type || (this.column_needed && isEmptyObj(this._column)) || !this.label
		},
		column_options() {
			const column_list = this.query.get_selectable_columns?.data?.message || []
			return column_list.map((c) => {
				return {
					...c,
					value: c.column,
					secondary_label: c.table_label,
				}
			})
		},
		filtered_columns() {
			if (isEmptyObj(this.type)) {
				return []
			}
			if (this.type.value === 'Sum' || this.type.value === 'Avg') {
				return this.column_options.filter((c) =>
					['int', 'decimal', 'bigint', 'float', 'double'].includes(c.type.toLowerCase())
				)
			}
		},
		column_needed() {
			return !isEmptyObj(this.type) && this.type.value !== 'Count'
		},
	},
	methods: {
		on_type_select(option) {
			this.type = option
			this.label += option.label + ' '
		},
		on_column_select(option) {
			this._column = option
			this.label += option.label
		},
		add_metric() {
			if (isEmptyObj(this.type)) {
				return
			}

			if (this.column_needed && isEmptyObj(this._column)) {
				return
			}

			if (!this.column_needed) {
				let column = this.get_count_column()
				this.$emit('column-select', column)
			}

			if (this.column_needed) {
				this._column.aggregation = this.type.value
				this.$emit('column-select', this._column)
			}
		},
		get_count_column() {
			if (this.column) {
				this.column.label = this.label
				this.column.aggregation = this.type.value
				return this.column
			}

			const table = this.query.doc.tables[0]
			return {
				type: 'Int',
				column: 'name',
				label: this.label,
				table: table.table,
				table_label: table.label,
				aggregation: this.type.value,
			}
		},
	},
}
</script>
