<script setup lang="ts">
import { TextInput } from 'frappe-ui'
import { __ } from '../../translation'
import { Check, ChevronLeft, Edit, Plus, Settings, XIcon } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { FIELDTYPES } from '../../helpers/constants'
import {
	AggregationType,
	ColumnMeasure,
	ColumnOption,
	ExpressionMeasure,
	Measure,
	MeasureDataType,
	aggregations,
} from '../../types/query.types'
import NewMeasureSelectorDialog from './NewMeasureSelectorDialog.vue'

const emit = defineEmits({ remove: () => true })
const props = defineProps<{
	label?: string
	columnOptions: ColumnOption[]
}>()

// True when at least one available column is a pre-aggregated measure (i.e. it
// came from a summarize/pivot_wider step in the source query). In this case we
// skip the "pick a function" step by pre-selecting `sum`, since the data is
// already aggregated and users just want to pick the column directly.
const sourceHasMeasures = computed(() => props.columnOptions.some((c) => c.is_measure))

const measure = defineModel<Measure>({
	required: true,
	default: () => {
		return {
			column_name: '',
			data_type: 'Decimal',
			measure_name: '',
			aggregation: '',
		}
	},
})

const columnMeasure = computed<ColumnMeasure | undefined>({
	get() {
		if ('column_name' in measure.value) {
			return measure.value as ColumnMeasure
		}
	},
	set(value) {
		measure.value = value!
	},
})

const expressionMeasure = computed<ExpressionMeasure | undefined>({
	get() {
		if ('expression' in measure.value) {
			return measure.value as ExpressionMeasure
		}
	},
	set(value) {
		measure.value = value!
	},
})

const searchQuery = ref('')

// Tracks whether the user manually clicked "back" (ChevronLeft) to change the
// aggregation. When true, we don't auto-fill the aggregation so the user can
// choose a different function.
const userResetAggregation = ref(false)

watchEffect(() => {
	if (!columnMeasure.value && !expressionMeasure.value) {
		resetMeasure()
	}
})

// When the source columns include pre-aggregated measures, pre-select `sum` as
// the aggregation so the picker opens straight to the column list — skipping
// the "pick a function" step that would otherwise produce confusing
// "sum of sum_of_revenue" labels.
// We skip this if the user explicitly clicked back to pick a different function.
watchEffect(() => {
	if (!sourceHasMeasures.value) return
	if (userResetAggregation.value) return
	const cm = columnMeasure.value
	if (cm && !cm.aggregation) {
		cm.aggregation = 'sum'
	}
})

watchEffect(() => {
	const cm = columnMeasure.value
	if (!cm) return

	const hasDefaultLabel =
		!cm.measure_name ||
		cm.measure_name.includes(`${cm.aggregation}_`) ||
		cm.measure_name.includes(cm.column_name)

	if (cm.aggregation && cm.column_name && hasDefaultLabel) {
		// If the column is already a pre-aggregated measure (flagged via is_measure on
		// the column option, or its name starts with an aggregation prefix), keep the
		// column name as-is rather than wrapping it as e.g. "sum_of_total_requests".
		const aggregationPrefixes = aggregations.map((a) => `${a}_`)
		const columnIsAlreadyMeasure =
			props.columnOptions.find((o) => o.value === cm.column_name)?.is_measure ||
			aggregationPrefixes.some((prefix) => cm.column_name.startsWith(prefix))
		cm.measure_name = columnIsAlreadyMeasure
			? cm.column_name
			: `${cm.aggregation}_of_${cm.column_name}`
	}
})

const showMeasureDialog = ref(false)
function updateMeasure(measureExpression: ExpressionMeasure) {
	measure.value = {
		expression: measureExpression.expression,
		measure_name: measureExpression.measure_name,
		data_type: measureExpression.data_type,
	}
	showMeasureDialog.value = false
}

const aggregationOptions: { label: string; value: AggregationType }[] = [
	{ label: __('Count of...'), value: 'count' },
	{ label: __('Sum of...'), value: 'sum' },
	{ label: __('Average of...'), value: 'avg' },
	{ label: __('Minimum of...'), value: 'min' },
	{ label: __('Maximum of...'), value: 'max' },
	{ label: __('Unique Count of...'), value: 'count_distinct' },
]

const columnOptions = computed(() => {
	const fn = (measure.value as ColumnMeasure).aggregation
	if (!fn) return []

	return props.columnOptions.filter((column) => {
		if (['sum', 'avg'].includes(fn)) {
			// Only allow numeric columns for sum and avg
			return FIELDTYPES.NUMBER.includes(column.data_type)
		}
		return true
	})
})

const filteredColumnOptions = computed(() => {
	if (!searchQuery.value) return columnOptions.value
	const query = searchQuery.value.toLowerCase()

	return columnOptions.value.filter((option) => option.label.toLowerCase().includes(query))
})

function getAggregationLabel(aggregation: AggregationType) {
	return aggregationOptions.find((option) => option.value === aggregation)?.label
}

function resetMeasure() {
	measure.value = {
		column_name: '',
		data_type: 'Decimal',
		measure_name: '',
		aggregation: '',
	}
}

// Called when the user explicitly clicks ChevronLeft to go back and pick a
// different aggregation function. We set a flag so the watchEffect above doesn't
// immediately re-fill `sum` and trap the user on the column list.
function resetAggregation() {
	userResetAggregation.value = true
	resetMeasure()
}

const label = ref('')
</script>

<template>
	<div class="flex items-end gap-1 overflow-hidden">
		<div class="flex-1 overflow-hidden">
			<Popover>
				<template #target="{ togglePopover, isOpen }">
					<div class="w-full space-y-1.5">
						<div v-if="props.label" class="text-xs text-gray-600">
							{{ props.label }}
						</div>
						<button
							class="flex h-7 w-full items-center justify-between gap-2 rounded bg-gray-100 py-1 px-2 text-base transition-colors hover:bg-gray-200 focus:ring-2 focus:ring-gray-400"
							@click="() => togglePopover()"
						>
							<div class="flex flex-1 items-center gap-2 overflow-hidden truncate">
								<span v-if="measure.measure_name">
									{{ measure.measure_name }}
								</span>
								<span v-else class="text-gray-500"> Select a column </span>
							</div>
						</button>
					</div>
				</template>

				<template #body="{ isOpen, togglePopover }">
					<div
						class="relative mt-1 overflow-hidden rounded-lg bg-white p-1.5 text-base shadow-2xl"
					>
						<template v-if="columnMeasure && !expressionMeasure">
							<span
								v-if="!columnMeasure.aggregation"
								class="block px-1.5 py-0.5 text-p-xs text-gray-600"
							>
								Select a Function
							</span>
							<div
								v-else-if="columnMeasure.aggregation"
								class="mb-1 flex items-center"
							>
								<Button class="!h-6 !w-6" @click.prevent.stop="resetAggregation">
									<template #icon>
										<ChevronLeft
											class="h-4 w-4 text-gray-700"
											stroke-width="1.5"
										/>
									</template>
								</Button>
								<span class="block px-1.5 py-0.5 text-p-xs text-gray-600">
									{{ getAggregationLabel(columnMeasure.aggregation) }}
								</span>
							</div>
							<div class="flex max-h-[15rem] flex-col overflow-y-scroll">
								<template v-if="!columnMeasure.aggregation">
									<div
										v-for="option in aggregationOptions"
										:key="option.value"
										class="flex h-7 flex-shrink-0 cursor-pointer items-center justify-between rounded px-2.5 text-base hover:bg-gray-100"
										@click.prevent.stop="
											() => {
												if (!columnMeasure) return
												columnMeasure.aggregation = option.value
												userResetAggregation = false
											}
										"
									>
										<span>{{ option.label }}</span>
										<span v-if="option.value === columnMeasure.aggregation">
											<Check
												class="h-4 w-4 text-gray-700"
												stroke-width="1.5"
											/>
										</span>
									</div>
								</template>

								<template v-if="columnMeasure.aggregation">
									<div class="sticky top-0 bg-white space-y-1 p-1">
										<TextInput
											v-model="searchQuery"
											placeholder="Search..."
											autocomplete="off"
										/>
									</div>
									<div
										v-for="option in filteredColumnOptions"
										:key="option.value"
										class="flex h-7 flex-shrink-0 cursor-pointer items-center justify-between rounded px-2.5 text-base hover:bg-gray-100"
										@click.prevent.stop="
											() => {
												;(measure as ColumnMeasure).column_name =
													option.value
												measure.data_type =
													option.data_type as MeasureDataType
												togglePopover()
											}
										"
									>
										<span>{{ option.label }}</span>
										<span v-if="option.value === columnMeasure.column_name">
											<Check
												class="h-4 w-4 text-gray-700"
												stroke-width="1.5"
											/>
										</span>
									</div>
								</template>
							</div>
						</template>

						<div
							v-if="expressionMeasure || !columnMeasure?.aggregation"
							:class="[!expressionMeasure ? 'mt-1 border-t pt-1' : '']"
						>
							<Button
								class="w-full"
								variant="ghost"
								:label="expressionMeasure ? 'Edit Expression' : 'Custom Expression'"
								@click=";(showMeasureDialog = true), togglePopover()"
							>
								<template #prefix>
									<component
										:is="expressionMeasure ? Edit : Plus"
										class="h-4 w-4 text-gray-700"
										stroke-width="1.5"
									/>
								</template>
							</Button>
						</div>
					</div>
				</template>
			</Popover>
		</div>
		<Popover v-if="measure.measure_name" placement="bottom-end">
			<template #target="{ togglePopover }">
				<Button @click="togglePopover">
					<template #icon>
						<Settings class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<template #body-main>
				<div class="flex w-[14rem] flex-col gap-2 p-2">
					<InlineFormControlLabel label="Label">
						<TextInput
							autocomplete="off"
							:modelValue="measure.measure_name"
							@update:modelValue="label = $event"
							@blur="measure.measure_name = label"
							@keydown.enter="measure.measure_name = label"
						/>
					</InlineFormControlLabel>

					<slot name="config-fields" />

					<div class="flex gap-1">
						<Button class="w-full" @click="emit('remove')" theme="red">
							<template #prefix>
								<XIcon class="h-4 w-4 text-red-700" stroke-width="1.5" />
							</template>
							Remove
						</Button>
					</div>
				</div>
			</template>
		</Popover>
		<Button v-else @click="emit('remove')">
			<template #icon>
				<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</Button>
	</div>

	<NewMeasureSelectorDialog
		v-if="showMeasureDialog"
		:model-value="Boolean(showMeasureDialog)"
		@update:model-value="!$event && (showMeasureDialog = false)"
		:column-options="props.columnOptions"
		:measure="measure as ExpressionMeasure"
		@select="updateMeasure"
	/>
</template>
