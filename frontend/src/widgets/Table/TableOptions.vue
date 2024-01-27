<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'

import DraggableList from '@/components/DraggableList.vue'
import DraggableListItemMenu from '@/components/DraggableListItemMenu.vue'
import { computed } from 'vue'
import TableColumnOptions from './TableColumnOptions.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
	columns: { type: Array, required: true },
})

const options = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

if (!options.value.columns) {
	options.value.columns = []
}
// handle legacy columns format
if (Array.isArray(options.value.columns) && typeof options.value.columns[0] === 'string') {
	options.value.columns = options.value.columns.map((column) => ({
		column,
		column_options: {},
	}))
}
options.value.columns.forEach((item) => {
	if (!item.column) item.column = item.label || item.value
	if (!item.column_options) item.column_options = {}
})

const columnOptions = computed(() => {
	return props.columns?.map((column) => ({
		label: column.label,
		value: column.label,
		description: column.type,
	}))
})

function updateColumns(columnOptions) {
	options.value.columns = columnOptions.map((option) => {
		const existingColumn = options.value.columns.find((c) => c.label === option.value)
		const column_options = existingColumn ? existingColumn.column_options : {}
		return {
			column: option.value,
			column_options,
		}
	})
}
</script>

<template>
	<div>
		<div class="mb-1 flex items-center justify-between">
			<label class="block text-xs text-gray-600">Columns</label>
			<Autocomplete
				:multiple="true"
				:options="columnOptions"
				:modelValue="options.columns"
				@update:model-value="updateColumns"
			>
				<template #target="{ togglePopover }">
					<Button variant="ghost" icon="plus" @click="togglePopover"></Button>
				</template>
			</Autocomplete>
		</div>

		<DraggableList
			group="columns"
			item-key="column"
			empty-text="No columns selected"
			v-model:items="options.columns"
		>
			<template #item-suffix="{ item, index }">
				<DraggableListItemMenu>
					<TableColumnOptions
						v-if="item.column_options && props.columns"
						:model-value="item.column_options"
						:column="props.columns.find((col) => col.label === item.column)"
						@update:model-value="options.columns[index].column_options = $event"
					/>
				</DraggableListItemMenu>
			</template>
		</DraggableList>
	</div>

	<FormControl
		type="text"
		label="Title"
		class="w-full"
		v-model="options.title"
		placeholder="Title"
	/>
	<Checkbox v-model="options.index" label="Show Index Row" />
	<Checkbox v-model="options.showTotal" label="Show Total Row" />
	<Checkbox v-model="options.filtersEnabled" label="Show Filter Row" />
</template>
