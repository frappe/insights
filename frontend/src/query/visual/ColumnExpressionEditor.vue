<script setup>
import { COLUMN_TYPES, FIELDTYPES, GRANULARITIES } from '@/utils'
import { parse } from '@/utils/expressions'
import { computed, defineProps, inject, reactive } from 'vue'
import ExpressionBuilder from './ExpressionBuilder.vue'
import { NEW_COLUMN } from './constants'
import { getSelectedTables } from './useAssistedQuery'

const emptyExpressionColumn = {
	...NEW_COLUMN,
	expression: {
		raw: '',
		ast: {},
	},
}

const assistedQuery = inject('assistedQuery')
const emit = defineEmits(['save', 'remove'])
const props = defineProps({ column: Object })

const propsColumn = props.column || emptyExpressionColumn
const column = reactive({
	...NEW_COLUMN,
	...propsColumn,
})
if (!column.expression) {
	column.expression = { ...emptyExpressionColumn.expression }
}

const isValid = computed(() => {
	if (!column.label || !column.type) return false
	if (!column.expression.raw) return false
	return true
})

const columnOptions = computed(() => {
	const selectedTables = getSelectedTables(assistedQuery)
	return assistedQuery.columnOptions.filter((c) => selectedTables.includes(c.table)) || []
})

function onSave() {
	if (!isValid.value) return
	emit('save', {
		...column,
		label: column.label.trim(),
		type: column.type.trim(),
		expression: {
			raw: column.expression.raw,
			ast: parse(column.expression.raw).ast,
		},
	})
}
</script>

<template>
	<div class="space-y-3 text-base">
		<ExpressionBuilder v-model="column.expression" :columnOptions="columnOptions" />

		<div class="grid grid-cols-2 gap-4">
			<FormControl
				type="text"
				label="Label"
				class="col-span-1"
				v-model="column.label"
				placeholder="Label"
				autocomplete="off"
			/>
			<FormControl
				label="Type"
				type="select"
				class="col-span-1"
				v-model="column.type"
				:options="COLUMN_TYPES"
			/>
			<div v-if="FIELDTYPES.DATE.includes(column.type)" class="col-span-1 space-y-1">
				<span class="mb-2 block text-sm leading-4 text-gray-700">Date Format</span>
				<Autocomplete
					:modelValue="column.granularity"
					placeholder="Date Format"
					:options="GRANULARITIES"
					@update:modelValue="(op) => (column.granularity = op.value)"
				/>
			</div>
		</div>

		<div class="flex flex-col justify-end gap-2 lg:flex-row">
			<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
			<Button variant="solid" :disabled="!isValid" @click="onSave"> Save </Button>
		</div>
	</div>
</template>
