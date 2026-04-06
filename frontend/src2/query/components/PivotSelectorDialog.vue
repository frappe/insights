<script setup lang="ts">
import { computed, inject, ref, watchEffect } from 'vue'
import DimensionPicker from '../../charts/components/DimensionPicker.vue'
import MeasurePicker from '../../charts/components/MeasurePicker.vue'
import { copy } from '../../helpers'
import {
	ColumnOption,
	Dimension,
	DimensionOption,
	Measure,
	PivotWiderArgs,
} from '../../types/query.types'
import { makeDimension } from '../helpers'
import { Query } from '../query'

const props = defineProps<{
	pivot?: PivotWiderArgs
}>()
const emit = defineEmits({ select: (args: PivotWiderArgs) => true })
const showDialog = defineModel()

const query = inject<Query>('query')!
const columnOptions = ref<ColumnOption[]>([])
query.getColumnsForSelection().then((cols) => (columnOptions.value = cols))

const dimensionOptions = computed<DimensionOption[]>(() => {
	return columnOptions.value
		.map((o) => ({ name: o.value, type: o.data_type }))
		.map(makeDimension)
		.map((o) => ({
			...o,
			label: o.dimension_name,
			value: o.column_name,
		}))
})

const rows = ref<Dimension[]>([])
const columns = ref<Dimension[]>([])
const values = ref<Measure[]>([])

if (props.pivot?.rows) rows.value = copy(props.pivot.rows)
if (props.pivot?.columns) columns.value = copy(props.pivot.columns)
if (props.pivot?.values) values.value = copy(props.pivot.values as Measure[])

watchEffect(() => {
	if (!rows.value.length) addRow()
	if (!columns.value.length) addColumn()
	if (!values.value.length) addValue()
})

function emptyDimension(): Dimension {
	return { column_name: '', data_type: 'String', granularity: 'month', dimension_name: '' }
}

function addRow() {
	rows.value.push(emptyDimension())
}
function addColumn() {
	columns.value.push(emptyDimension())
}
function addValue() {
	values.value.push({ measure_name: '', column_name: '', aggregation: '', data_type: 'Decimal' })
}

function isValidMeasure(m: Measure) {
	return ('column_name' in m && m.column_name) || ('expression' in m && m.expression.expression)
}

const areRowsValid = computed(() => rows.value.every((d) => d.column_name))
const areColumnsValid = computed(() => columns.value.every((d) => d.column_name))
const areValuesValid = computed(() => values.value.every((m) => isValidMeasure(m)))
const canConfirm = computed(
	() => areRowsValid.value && areColumnsValid.value && areValuesValid.value,
)

function resetSelections() {
	rows.value = []
	columns.value = []
	values.value = []
}

function confirmSelections() {
	emit('select', {
		rows: rows.value.filter((d) => d.column_name),
		columns: columns.value.filter((d) => d.column_name),
		values: values.value.filter((m) => isValidMeasure(m)),
	})
	showDialog.value = false
}
</script>

<template>
	<Dialog :modelValue="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<div class="min-w-[36rem] rounded-lg bg-white px-4 pb-6 pt-5 text-base sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Pivot</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md" />
				</div>

				<div class="flex flex-col gap-4">
					<!-- Three columns: Rows | Columns | Values -->
					<div class="flex gap-4">
						<!-- Rows -->
						<div class="flex-1 flex-shrink-0">
							<p class="mb-1.5 text-p-sm text-gray-600">Rows</p>
							<div class="flex flex-col gap-2">
								<DimensionPicker
									v-for="(row, idx) in rows"
									:key="idx"
									v-model="rows[idx]"
									:options="dimensionOptions"
									@remove="rows.splice(idx, 1)"
								/>
							</div>
							<button
								class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
								@click="addRow"
							>
								+ Add
							</button>
						</div>

						<!-- Columns -->
						<div class="flex-1 flex-shrink-0">
							<p class="mb-1.5 text-p-sm text-gray-600">Columns</p>
							<div class="flex flex-col gap-2">
								<DimensionPicker
									v-for="(col, idx) in columns"
									:key="idx"
									v-model="columns[idx]"
									:options="dimensionOptions"
									@remove="columns.splice(idx, 1)"
								/>
							</div>
							<button
								class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
								@click="addColumn"
							>
								+ Add
							</button>
						</div>

						<!-- Values -->
						<div class="flex-1 flex-shrink-0">
							<p class="mb-1.5 text-p-sm text-gray-600">Values</p>
							<div class="flex flex-col gap-2">
								<MeasurePicker
									v-for="(value, idx) in values"
									:key="idx"
									v-model="values[idx]"
									:columnOptions="columnOptions"
									@remove="values.splice(idx, 1)"
								/>
							</div>
							<button
								class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
								@click="addValue"
							>
								+ Add
							</button>
						</div>
					</div>

					<div class="mt-2 flex justify-end">
						<div class="flex gap-2">
							<Button label="Clear" variant="outline" @click="resetSelections" />
							<Button
								label="Done"
								variant="solid"
								:disabled="!canConfirm"
								@click="confirmSelections"
							/>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
