<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import Checkbox from '@/components/Controls/Checkbox.vue'
import Color from '@/components/Controls/Color.vue'
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
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
	return options.value.yAxis.map((item) => ({ column: item }))
}

const yAxis = computed({
	get: () => (deprecatedOptions.value ? convertDeprecatedOptions() : options.value.yAxis),
	set: (value) => (options.value.yAxis = value),
})
const areAllColumnsSelected = computed(() => {
	return yAxis.value?.length && yAxis.value?.length === valueOptions.value?.length
})
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
			<span class="mb-2 block text-sm leading-4 text-gray-700">X Axis</span>
			<Autocomplete v-model="options.xAxis" :returnValue="true" :options="indexOptions" />
		</div>
		<div class="relative max-h-[15rem] space-y-2 overflow-hidden overflow-y-scroll">
			<div class="sticky top-0 -mt-1 flex items-center justify-between bg-white">
				<span class="block text-sm leading-4 text-gray-700">Y Axis</span>
				<Autocomplete
					:modelValue="yAxis?.map((item) => item.column)"
					:multiple="true"
					:returnValue="true"
					:options="valueOptions"
					@update:model-value="yAxis = $event.map((item) => ({ column: item }))"
				>
					<template #target="{ togglePopover }">
						<Button variant="ghost" icon="plus" @click="togglePopover" />
					</template>
					<template #footer>
						<div class="flex items-center justify-end">
							<Button
								v-if="!areAllColumnsSelected"
								variant="subtle"
								@click="
									yAxis = valueOptions.map((item) => ({ column: item.value }))
								"
							>
								Select All
							</Button>
						</div>
					</template>
				</Autocomplete>
			</div>
			<div class="flex w-full flex-col space-y-2">
				<div class="flex flex-1" v-for="(series, index) in yAxis" :key="index">
					<SeriesOption
						seriesType="line"
						:modelValue="series"
						@remove="yAxis.splice(yAxis.indexOf(series), 1)"
					/>
				</div>
			</div>
		</div>

		<div v-if="yAxis?.length == 2" class="space-y-2 text-gray-600">
			<Checkbox v-model="options.splitYAxis" label="Split Y Axis" />
		</div>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Reference Line</span>
			<Autocomplete
				:modelValue="options.referenceLine"
				:options="['Average', 'Median', 'Min', 'Max']"
				@update:modelValue="options.referenceLine = $event.value"
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
