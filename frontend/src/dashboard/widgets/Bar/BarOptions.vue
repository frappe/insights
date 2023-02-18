<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
import Color from '@/components/Controls/Color.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'
import { FIELDTYPES } from '@/utils'
import { computed, inject } from 'vue'
import QueryOption from '../QueryOption.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
})

const options = computed({
	get() {
		return props.modelValue
	},
	set(value) {
		emit('update:modelValue', value)
	},
})

const dashboard = inject('dashboard')
const queryResource = computed(() => {
	if (!options.value.query) return []
	return dashboard.queries[options.value.query]
})
const indexOptions = computed(() => {
	return queryResource.value?.resultColumns
		?.filter((column) => !FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.column,
			value: column.column,
			description: column.type,
		}))
})
const valueOptions = computed(() => {
	return queryResource.value?.resultColumns
		?.filter((column) => FIELDTYPES.NUMBER.includes(column.type))
		.map((column) => ({
			label: column.column,
			value: column.column,
			description: column.type,
		}))
})
</script>

<template>
	<div class="space-y-4">
		<QueryOption v-model="options.query" />
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
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Y Axis</span>
			<ListPicker
				:value="options.yAxis"
				:options="valueOptions"
				@change="options.yAxis = $event.map((item) => item.value)"
			/>
		</div>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Reference Line</span>
			<Autocomplete
				v-model="options.referenceLine"
				:options="['Average', 'Median', 'Min', 'Max']"
			/>
		</div>

		<Color label="Colors" v-model="options.colors" :max="options.yAxis?.length || 1" multiple />

		<Input
			type="select"
			label="Rotate Labels"
			v-model="options.rotateLabels"
			:options="['0', '45', '90']"
		/>

		<Checkbox v-model="options.stack" label="Stack Values" />

		<Checkbox v-model="options.invertAxis" label="Switch X and Y Axis" />
	</div>
</template>
