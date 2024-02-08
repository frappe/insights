<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import ColorPalette from '@/components/Controls/ColorPalette.vue'
import DraggableList from '@/components/DraggableList.vue'
import DraggableListItemMenu from '@/components/DraggableListItemMenu.vue'
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
import SeriesOption from '../SeriesOption.vue'

const emit = defineEmits(['update:modelValue'])
const options = defineModel('options')
const props = defineProps({
	seriesType: { type: String },
	options: { type: Object, required: true },
	columns: { type: Array, required: true },
})

if (!options.value.xAxis) options.value.xAxis = []
if (!options.value.yAxis) options.value.yAxis = []

if (typeof options.value.xAxis === 'string') {
	options.value.xAxis = [{ column: options.value.xAxis }]
}
if (typeof options.value.yAxis === 'string') {
	options.value.yAxis = [{ column: options.value.yAxis }]
}

if (Array.isArray(options.value.xAxis) && typeof options.value.xAxis[0] === 'string') {
	options.value.xAxis = options.value.xAxis.map((column) => ({ column }))
}
if (Array.isArray(options.value.yAxis) && typeof options.value.yAxis[0] === 'string') {
	options.value.yAxis = options.value.yAxis.map((column) => ({ column }))
}

options.value.yAxis.forEach((item) => {
	if (!item.series_options) item.series_options = {}
})

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

function updateXAxis(columnOptions) {
	if (!columnOptions) {
		options.value.xAxis = []
		return
	}
	options.value.xAxis = columnOptions.map((option) => {
		return { column: option.value }
	})
}
</script>

<template>
	<FormControl
		type="text"
		label="Title"
		class="w-full"
		v-model="options.title"
		placeholder="Title"
	/>
	<div>
		<div class="mb-1 flex items-center justify-between">
			<label class="block text-xs text-gray-600">X Axis</label>
			<Autocomplete
				:multiple="true"
				:options="indexOptions"
				:modelValue="options.xAxis?.map((item) => item.column) || []"
				@update:model-value="updateXAxis"
			>
				<template #target="{ togglePopover }">
					<Button variant="ghost" icon="plus" @click="togglePopover" />
				</template>
			</Autocomplete>
		</div>
		<DraggableList
			group="xAxis"
			item-key="column"
			empty-text="No columns selected"
			v-model:items="options.xAxis"
		/>
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
						:seriesType="props.seriesType"
						:modelValue="item.series_options || {}"
						@update:modelValue="options.yAxis[index].series_options = $event"
					/>
				</DraggableListItemMenu>
			</template>
		</DraggableList>
	</div>

	<div v-if="options.yAxis?.length == 2" class="space-y-2 text-gray-600">
		<Checkbox v-model="options.splitYAxis" label="Split Y Axis" />
	</div>

	<div>
		<label class="mb-1.5 block text-xs text-gray-600">Reference Line</label>
		<Autocomplete
			:modelValue="options.referenceLine"
			:options="['Average', 'Median', 'Min', 'Max']"
			@update:modelValue="options.referenceLine = $event?.value"
		/>
	</div>

	<ColorPalette v-model="options.colors" />
</template>
