<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import Checkbox from '@/components/Controls/Checkbox.vue'
import DraggableList from '@/components/DraggableList.vue'
import DraggableListItemMenu from '@/components/DraggableListItemMenu.vue'
import { FIELDTYPES } from '@/utils'
import { computed, onUpdated } from 'vue'
import SeriesOption from '../SeriesOption.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
	columns: { type: Array, required: true },
})

const options = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

if (!options.value.yAxis) options.value.yAxis = []

const indexOptions = computed(() => {
	return props.columns
		?.filter((column) => !FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.label,
			value: column.label,
			description: column.type,
		}))
})
const valueOptions = computed(() => {
	return props.columns
		?.filter((column) => FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.label,
			value: column.label,
			description: column.type,
		}))
})

function updateYAxis(columnOptions) {
	if (!columnOptions) {
		options.value.yAxis = []
		return
	}
	options.value.yAxis = columnOptions.map((option) => {
		const existingColumn = options.value.yAxis?.find((c) => c.column === option.value)
		const series_options = existingColumn ? existingColumn.series_options : {}
		return { column: option.value, series_options }
	})
}
</script>

<template>
	<div class="space-y-4">
		<FormControl
			type="text"
			label="Title"
			class="w-full"
			v-model="options.title"
			placeholder="Title"
		/>
		<div>
			<label class="mb-1.5 block text-xs text-gray-600">X Axis</label>
			<Autocomplete v-model="options.xAxis" :returnValue="true" :options="indexOptions" />
		</div>

		<div>
			<div class="mb-1 flex items-center justify-between">
				<label class="block text-xs text-gray-600">Y Axis</label>
				<Autocomplete
					:multiple="true"
					:options="valueOptions"
					:modelValue="options.yAxis?.map((item) => item.column) || []"
					@update:model-value="updateYAxis"
				>
					<template #target="{ togglePopover }">
						<Button variant="ghost" icon="plus" @click="togglePopover" />
					</template>
				</Autocomplete>
			</div>
			<DraggableList
				group="yAxis"
				item-key="column"
				empty-text="No columns selected"
				v-model:items="options.yAxis"
			>
				<template #item-suffix="{ item, index }">
					<DraggableListItemMenu>
						<SeriesOption
							:modelValue="item.series_options || {}"
							@update:modelValue="options.yAxis[index].series_options = $event"
						/>
					</DraggableListItemMenu>
				</template>
			</DraggableList>
		</div>

		<Checkbox v-model="options.splitYAxis" label="Split Y Axis" />
		<div>
			<label class="mb-1.5 block text-xs text-gray-600">Reference Line</label>
			<Autocomplete
				:modelValue="options.referenceLine"
				:options="['Average', 'Median', 'Min', 'Max']"
				@update:modelValue="options.referenceLine = $event.value"
			/>
		</div>
	</div>
</template>
