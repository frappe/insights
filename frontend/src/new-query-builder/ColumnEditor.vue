<script setup>
import { AGGREGATIONS, FIELDTYPES, GRANULARITIES } from '@/utils'
import { defineProps, inject, reactive, ref, computed } from 'vue'
import ColumnExpressionEditor from './ColumnExpressionEditor.vue'
import { NEW_COLUMN } from './constants'

const emit = defineEmits(['save', 'discard', 'remove'])
const props = defineProps({ column: Object })

const builder = inject('builder')
const query = inject('query')

const activeTab = ref('Simple')
const column = reactive({
	...NEW_COLUMN,
	...props.column,
})
if (column.expression?.raw) {
	activeTab.value = 'Expression'
} else if (!column.aggregation) {
	column.aggregation = 'group by'
}

function onColumnChange(option) {
	column.table = option.table
	column.table_label = option.table_label
	column.column = option.column
	column.label = option.label
	column.alias = option.alias || option.label
	column.type = option.type
}

const isValidColumn = computed(() => {
	if (!column.label || !column.type) return false
	if (column.expression?.raw && column.expression?.ast) return true
	if (column.table && column.column) return true
	return false
})
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<div
			class="flex h-8 w-full cursor-pointer select-none items-center rounded bg-gray-100 p-1"
		>
			<div
				v-for="(tab, idx) in ['Simple', 'Expression']"
				class="flex h-full flex-1 items-center justify-center px-4 text-sm transition-all"
				:class="activeTab === tab ? 'rounded bg-white shadow' : ''"
				@click.prevent.stop="activeTab = tab"
			>
				{{ tab }}
			</div>
		</div>
		<template v-if="activeTab == 'Expression'">
			<ColumnExpressionEditor v-model:column="column" />
		</template>
		<template v-if="activeTab == 'Simple'">
			<div class="space-y-1">
				<span class="text-sm font-medium text-gray-700">Aggregation</span>
				<Autocomplete
					:modelValue="column.aggregation"
					placeholder="Aggregation"
					:options="AGGREGATIONS"
					@update:modelValue="(op) => (column.aggregation = op.val)"
				/>
			</div>
			<div class="space-y-1">
				<span class="text-sm font-medium text-gray-700">Column</span>
				<Autocomplete
					:modelValue="{
						...column,
						value: `${column.table}.${column.column}`,
					}"
					placeholder="Column"
					:options="query.columnOptions"
					@update:modelValue="onColumnChange"
				/>
			</div>
		</template>
		<div v-if="FIELDTYPES.DATE.includes(column.type)" class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Date Format</span>
			<Autocomplete
				:modelValue="column.granularity"
				placeholder="Date Format"
				:options="GRANULARITIES"
				@update:modelValue="(op) => (column.granularity = op.value)"
			/>
		</div>
		<div class="flex justify-between">
			<Button variant="outline" @click="emit('discard')">Discard</Button>
			<div class="flex gap-2">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button variant="solid" :disabled="!isValidColumn" @click="emit('save', column)">
					Save
				</Button>
			</div>
		</div>
	</div>
</template>
