<script setup>
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
const columnOptions = computed(() => {
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
			<span class="mb-2 block text-sm leading-4 text-gray-700">Number Column</span>
			<Autocomplete v-model.value="options.column" :options="columnOptions" />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Prefix</span>
			<Input type="text" v-model="options.prefix" placeholder="Enter a prefix..." />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Suffix</span>
			<Input type="text" v-model="options.suffix" placeholder="Enter a suffix..." />
		</div>
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Decimals</span>
			<Input type="number" v-model="options.decimals" placeholder="Enter a number..." />
		</div>
	</div>
</template>
