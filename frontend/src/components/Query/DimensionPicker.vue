<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				v-model="dimension.column"
				:options="columnOptions"
				placeholder="Select a column..."
				@selectOption="onColumnSelect"
			/>
		</div>
		<div v-if="dimension.label" class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Label</div>
			<Input
				type="text"
				v-model="dimension.label"
				class="h-8 placeholder:text-sm"
				placeholder="Enter a label..."
			/>
		</div>
		<div class="flex justify-end space-x-2">
			<Button
				v-if="row_name"
				class="text-red-500"
				appearance="white"
				@click="
					() => {
						query.removeColumn({ column: dimension.column })
						$emit('close')
					}
				"
			>
				Remove
			</Button>
			<Button @click="addDimension" appearance="primary" :disabled="addDisabled">
				{{ row_name ? 'Edit' : 'Add ' }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import { isEmptyObj } from '@/utils'
import Autocomplete from '@/components/Autocomplete.vue'

import { computed, inject, onMounted, reactive, ref } from 'vue'

const query = inject('query')

const emit = defineEmits(['column-select', 'close'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
	},
})

const dimension = reactive({
	column: props.column,
	label: props.column.label,
})
// for editing a dimension
const row_name = ref(props.column.name)

onMounted(() => query.fetchColumns())

const addDisabled = computed(() => {
	return isEmptyObj(dimension.column) || !dimension.label
})

const columnOptions = computed(() => {
	return query.fetchColumnsData.value?.map((c) => {
		return {
			...c,
			value: c.column,
			description: c.table_label,
		}
	})
})

function onColumnSelect(option) {
	dimension.column = option ? option : {}
	dimension.label =
		!dimension.label && dimension.column.label ? dimension.column.label : dimension.label

	dimension.column.name = row_name.value
}
function addDimension() {
	if (isEmptyObj(dimension.column)) {
		return
	}

	dimension.column.label = dimension.label
	dimension.column.aggregation = 'Group By'
	emit('column-select', dimension.column)
}
</script>
