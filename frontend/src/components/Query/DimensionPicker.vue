<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				id="column"
				v-model="column"
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
			<Button v-if="column" class="text-red-500" appearance="white" @click="query.remove_column.submit({ column })">
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
			_column: this.column || null,
			label: this.column?.label || '',
		}
	},
	mounted() {
		this.query.get_selectable_columns.fetch()
	},
	computed: {
		add_disabled() {
			return isEmptyObj(this._column) || !this.label
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
			// return all columns except numeric columns
			return this.column_options.filter(
				(c) => !['int', 'decimal', 'bigint', 'float', 'double'].includes(c.type.toLowerCase())
			)
		},
	},
	methods: {
		on_column_select(option) {
			this._column = option
			this.label = !this.label ? option.label : this.label
		},
		add_dimension() {
			if (isEmptyObj(this._column)) {
				return
			}

			this._column.label = this.label
			this._column.aggregation = 'Group By'
			this.$emit('column-select', this._column)
		},
	},
}
</script>
