<script setup>
import { computed } from 'vue'
import DraggableList from '@/components/DraggableList.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: { type: Object, required: true },
	columns: { type: Array, required: true },
})

const options = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
if (!options.value.rows) options.value.rows = []
if (!options.value.columns) options.value.columns = []
if (!options.value.values) options.value.values = []

const columnOptions = computed(() => {
	return props.columns?.map((column) => ({
		label: column.label,
		value: column.label,
		description: column.type,
	}))
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
			<div class="mb-1 flex items-center justify-between">
				<label class="block text-xs text-gray-600">Rows</label>
				<Autocomplete :multiple="true" v-model="options.rows" :options="columnOptions">
					<template #target="{ togglePopover }">
						<Button variant="ghost" icon="plus" @click="togglePopover"></Button>
					</template>
				</Autocomplete>
			</div>

			<DraggableList
				v-model:items="options.rows"
				group="columnOptions"
				empty-text="No rows selected"
			>
			</DraggableList>
		</div>

		<div>
			<div class="mb-1 flex items-center justify-between">
				<label class="block text-xs text-gray-600">Columns</label>
				<Autocomplete :multiple="true" v-model="options.columns" :options="columnOptions">
					<template #target="{ togglePopover }">
						<Button variant="ghost" icon="plus" @click="togglePopover"></Button>
					</template>
				</Autocomplete>
			</div>

			<DraggableList
				v-model:items="options.columns"
				group="columnOptions"
				emtpy-text="No columns selected"
			>
			</DraggableList>
		</div>

		<div>
			<div class="mb-1 flex items-center justify-between">
				<label class="block text-xs text-gray-600">Values</label>
				<Autocomplete :multiple="true" v-model="options.values" :options="columnOptions">
					<template #target="{ togglePopover }">
						<Button variant="ghost" icon="plus" @click="togglePopover"></Button>
					</template>
				</Autocomplete>
			</div>

			<DraggableList
				v-model:items="options.values"
				group="columnOptions"
				emtpy-text="No values selected"
			>
			</DraggableList>
		</div>
	</div>
</template>
