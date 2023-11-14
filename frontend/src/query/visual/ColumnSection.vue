<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { AlignCenter, Calendar, CalendarClock, CaseUpper, Combine, Hash, X } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import ColumnEditor from './ColumnEditor.vue'
import { NEW_COLUMN } from './constants'
import { fieldtypesToIcon } from '@/utils'

const query = inject('query')
const builder = inject('builder')

const columns = computed(() => builder.query.columns)
const columnRefs = ref(null)
const activeColumnIdx = ref(null)

function onColumnSelect(column) {
	if (!column) return
	if (columns.value.find((c) => c.table === column.table && c.column === column.column)) {
		return
	}
	builder.addColumns([column])
}

function onRemoveColumn() {
	builder.removeColumnAt(activeColumnIdx.value)
	activeColumnIdx.value = null
}
function onSaveColumn(column) {
	builder.updateColumnAt(activeColumnIdx.value, column)
	activeColumnIdx.value = null
}
function onAddColumnExpression() {
	builder.addColumns([
		{
			...NEW_COLUMN,
			expression: {
				raw: '',
				ast: {},
			},
		},
	])
	activeColumnIdx.value = columns.value.length - 1
}
function isValidColumn(column) {
	const isExpression = column.expression?.raw
	return column.label && column.type && (isExpression || (column.table && column.column))
}
</script>

<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<div class="flex items-center space-x-1.5">
				<Combine class="h-4 w-4 text-gray-600" />
				<p class="font-medium">Summarize</p>
			</div>
			<Autocomplete
				:modelValue="columns"
				:options="query.columnOptions"
				bodyClasses="!w-[16rem]"
				@update:modelValue="onColumnSelect"
			>
				<template #target="{ togglePopover }">
					<Button variant="outline" icon="plus" @click="togglePopover"></Button>
				</template>
				<template #footer="{ togglePopover }">
					<Button
						class="w-full"
						variant="ghost"
						iconLeft="plus"
						@click="onAddColumnExpression() || togglePopover()"
					>
						Custom Expression
					</Button>
				</template>
			</Autocomplete>
		</div>
		<div class="space-y-2">
			<div
				ref="columnRefs"
				v-for="(column, idx) in columns"
				:key="idx"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 hover:shadow"
				:class="
					activeColumnIdx === idx
						? 'border-gray-500 bg-white shadow-sm ring-1 ring-gray-400'
						: ''
				"
				@click="activeColumnIdx = columns.indexOf(column)"
			>
				<div class="flex w-full items-center overflow-hidden">
					<div class="flex w-full space-x-2 truncate" v-if="isValidColumn(column)">
						<component
							:is="fieldtypesToIcon[column.type]"
							class="h-4 w-4 text-gray-600"
						/>
						<div>{{ column.label }}</div>
					</div>
					<div v-else class="text-gray-600">Select a column</div>
				</div>
				<div class="flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
						@click.prevent.stop="builder.removeColumnAt(idx)"
					/>
				</div>
			</div>
		</div>
	</div>

	<UsePopover
		v-if="columnRefs?.[activeColumnIdx]"
		:show="activeColumnIdx !== null"
		@update:show="activeColumnIdx = null"
		:target-element="columnRefs[activeColumnIdx]"
	>
		<div class="w-[20rem] rounded bg-white text-base shadow-2xl">
			<ColumnEditor
				:column="columns[activeColumnIdx]"
				@discard="activeColumnIdx = null"
				@remove="onRemoveColumn"
				@save="onSaveColumn"
			/>
		</div>
	</UsePopover>
</template>
