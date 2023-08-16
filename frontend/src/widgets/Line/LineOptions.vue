<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
import Color from '@/components/Controls/Color.vue'
import DragHandleIcon from '@/components/Icons/DragHandleIcon.vue'
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
import Draggable from 'vuedraggable'
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

const deprecatedOptions = computed(() => {
	return options.value?.yAxis?.every((item) => typeof item === 'string')
})
function convertDeprecatedOptions() {
	options.value.yAxis = options.value.yAxis.map((item) => ({ column: item }))
}

const yAxis = computed({
	get: () => (deprecatedOptions.value ? convertDeprecatedOptions() : options.value.yAxis),
	set: (value) => (options.value.yAxis = value),
})
</script>

<template>
	<div class="space-y-4">
		<Input
			type="text"
			label="Title"
			class="w-full"
			v-model="options.title"
			placeholder="Title"
		/>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">X Axis</span>
			<Autocomplete v-model="options.xAxis" :options="indexOptions" />
		</div>
		<div class="space-y-2">
			<span class="mb-2 block text-sm leading-4 text-gray-700">Y Axis</span>
			<Draggable
				:modelValue="yAxis"
				group="yAxis"
				itemKey="column"
				handle=".handle"
				class="flex w-full flex-col space-y-2"
			>
				<template #item="{ element: series }">
					<div class="flex flex-1">
						<DragHandleIcon
							class="handle mr-1 h-4 w-4 flex-shrink-0 rotate-90 cursor-grab self-center text-gray-500"
						/>
						<SeriesOption
							:modelValue="series"
							:options="valueOptions"
							@remove="yAxis.splice(yAxis.indexOf(series), 1)"
						/>
					</div>
				</template>
			</Draggable>
			<div>
				<span
					v-if="options.splitYAxis ? yAxis.length < 2 : true"
					class="cursor-pointer text-sm text-gray-500 hover:text-gray-700"
					@click="yAxis ? yAxis.push({ column: '' }) : (yAxis = [{ column: '' }])"
				>
					+ Add Series
				</span>
			</div>
		</div>

		<div v-if="yAxis?.length == 2" class="space-y-2 text-gray-600">
			<Checkbox v-model="options.splitYAxis" label="Split Y Axis" />
		</div>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Reference Line</span>
			<Autocomplete
				v-model="options.referenceLine"
				:options="['Average', 'Median', 'Min', 'Max']"
			/>
		</div>

		<Color label="Colors" v-model="options.colors" :max="options.yAxis?.length || 1" multiple />

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.smoothLines" label="Enable Curved Lines" />
		</div>

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.showPoints" label="Show Data Points" />
		</div>

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="options.showArea" label="Show Area" />
		</div>
	</div>
</template>
