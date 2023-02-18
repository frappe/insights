<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'
import { computedEager } from '@vueuse/core'
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
	return queryResource.value?.resultColumns?.map((column) => ({
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
			<span class="mb-2 block text-sm leading-4 text-gray-700">Columns</span>
			<ListPicker
				:options="columnOptions"
				:value="options.columns"
				@change="options.columns = $event.map((item) => item.value)"
			/>
		</div>
		<Checkbox v-model="options.index" label="Show Index" />
		<Checkbox v-model="options.showTotal" label="Show Total" />
	</div>
</template>
