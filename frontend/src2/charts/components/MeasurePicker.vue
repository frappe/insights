<script setup lang="ts">
import { TextInput } from 'frappe-ui'
import { __ } from '../../translation'
import { Check, ChevronLeft, Edit, Plus, Settings, XIcon } from 'lucide-vue-next'
import { computed, h, ref } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { dialogs } from '../../helpers/confirm_dialog'
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

const emit = defineEmits({ remove: () => true, 'dialog-open': () => true })
const props = defineProps<{
	label?: string
	columnOptions: ColumnOption[]
	enableFormat?: boolean
	/** Width of the settings popover, for a `config-fields` slot that needs more. */
	configWidth?: string
}>()

/**
 * The settings popover holds a labeled row, so it is as wide as the widest
 * control that row carries: the number format group, at 10rem, beside a label
 * column of 30%. Narrower than this and the group runs past the edge.
 */
const CONFIG_WIDTH = '17rem'

const formatOptions = [
	{ label: __('Normal'), value: '' },
	{ label: __('Percent'), value: 'percent' },
	{ label: __('Currency'), value: 'currency' },
]

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

// An empty slot is a column measure nobody has filled in yet. Reading it as
// neither kind is what made the picker write a measure the moment it mounted —
// one autosave and two re-runs of the chart data for opening a chart.
const columnMeasure = computed<ColumnMeasure | undefined>({
	get() {
		if ('expression' in measure.value) return
		return measure.value as ColumnMeasure
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
const aggregationPrefixes = aggregations.map((aggregation) => `${aggregation}_`)
const lastAutoMeasureName = ref('')

// Tracks whether the user manually clicked "back" (ChevronLeft) to change the
// aggregation. When true, we don't auto-fill the aggregation so the user can
// choose a different function.
const userResetAggregation = ref(false)

function isPreAggregatedMeasure(columnName: string) {
	return (
		props.columnOptions.find((option) => option.value === columnName)?.is_measure ||
		aggregationPrefixes.some((prefix) => columnName.startsWith(prefix))
	)
}

function getAutoMeasureName(columnMeasure: ColumnMeasure) {
	if (!columnMeasure.aggregation || !columnMeasure.column_name) return ''

	return isPreAggregatedMeasure(columnMeasure.column_name)
		? columnMeasure.column_name
		: `${columnMeasure.aggregation}_of_${columnMeasure.column_name}`
}

/**
 * The aggregation the picker is drawing, which is not always one the measure
 * carries.
 *
 * A source whose columns are already measures opens on the column list under
 * `sum`, skipping the "pick a function" step that would otherwise name a column
 * "sum of sum_of_revenue". That is what the picker shows, not what it stores:
 * nothing is written until the author picks a column. A rule the picker wrote
 * while it was setting itself up left every chart dirty for being opened — one
 * autosave and two re-runs of the chart data.
 */
const shownAggregation = computed<AggregationType | ''>(() => {
	const carried = columnMeasure.value?.aggregation
	if (carried) return carried as AggregationType
	return sourceHasMeasures.value && !userResetAggregation.value ? 'sum' : ''
})

/** The author picked a function. Still nothing to store: a function names no column. */
function pickAggregation(aggregation: AggregationType) {
	userResetAggregation.value = false
	const cm = columnMeasure.value
	if (cm) cm.aggregation = aggregation
}

/** The author picked a column. This is the write. */
function pickColumn(option: ColumnOption) {
	const cm = columnMeasure.value
	if (!cm) return

	cm.aggregation = shownAggregation.value
	cm.column_name = option.value
	cm.data_type = option.data_type as MeasureDataType

	// The author's own label stands. Only the name this picker last wrote, or no
	// name at all, is replaced.
	const autoMeasureName = getAutoMeasureName(cm)
	const hasDefaultLabel =
		!cm.measure_name ||
		cm.measure_name === autoMeasureName ||
		cm.measure_name === lastAutoMeasureName.value
	if (autoMeasureName && hasDefaultLabel) {
		cm.measure_name = autoMeasureName
		lastAutoMeasureName.value = autoMeasureName
	}
}

let dialogCount = 0

/**
 * The expression dialog is mounted at the app root, not under this picker: a
 * picker can sit inside a popover — this one nests in the number card's
 * settings — and a popover unmounts its content when it closes, taking a dialog
 * rendered there with it. Every popover over the dialog closes first, this
 * picker's own and, through `dialog-open`, the one it is nested in.
 */
function openMeasureDialog(closePopover: () => void) {
	closePopover()
	emit('dialog-open')

	const dialog = h(NewMeasureSelectorDialog, {
		key: `measure-expression-${++dialogCount}`,
		modelValue: true,
		columnOptions: props.columnOptions,
		measure: expressionMeasure.value,
		'onUpdate:modelValue': (open: boolean) => !open && closeMeasureDialog(),
		onSelect: (measureExpression: ExpressionMeasure) => {
			updateMeasure(measureExpression)
			closeMeasureDialog()
		},
	})
	function closeMeasureDialog() {
		dialogs.value = dialogs.value.filter((mounted) => mounted !== dialog)
	}
	dialogs.value.push(dialog)
}

/**
 * Writes onto the measure the picker holds instead of emitting: by the time the
 * dialog answers, the popover can have unmounted the picker, and an emit from an
 * unmounted picker reaches nobody.
 */
function updateMeasure(measureExpression: ExpressionMeasure) {
	const written = measure.value as Partial<ColumnMeasure> & Partial<ExpressionMeasure>
	delete written.column_name
	delete written.aggregation
	written.expression = measureExpression.expression
	written.measure_name = measureExpression.measure_name
	written.data_type = measureExpression.data_type
}

const aggregationOptions: { label: string; value: AggregationType }[] = [
	{ label: __('Count of...'), value: 'count' },
	{ label: __('Sum of...'), value: 'sum' },
	{ label: __('Average of...'), value: 'avg' },
	{ label: __('Minimum of...'), value: 'min' },
	{ label: __('Maximum of...'), value: 'max' },
	{ label: __('Unique count of...'), value: 'count_distinct' },
]

const columnOptions = computed(() => {
	const fn = shownAggregation.value
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

// a currency code is text, so only text columns are offered
const currencyColumnOptions = computed(() => [
	{ label: __('Site currency'), value: '' },
	...props.columnOptions
		.filter((column) => FIELDTYPES.TEXT.includes(column.data_type))
		.map((column) => ({ label: column.label, value: column.value })),
])

function getAggregationLabel(aggregation: AggregationType | '') {
	if (!aggregation) return undefined
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

// The author clicked back to pick a different function. The flag is what stops
// `shownAggregation` from putting `sum` straight back and keeping them on the
// column list.
function resetAggregation() {
	userResetAggregation.value = true
	resetMeasure()
}

const label = ref(measure.value.measure_name)

function handleRemove() {
	measure.value = {
		column_name: '',
		data_type: 'Decimal',
		measure_name: '',
		aggregation: '',
	}
	emit('remove')
}
</script>

<template>
	<div class="flex min-w-0 items-end gap-1">
		<div class="min-w-0 flex-1">
			<Popover bare match-trigger-width>
				<template #trigger>
					<div class="w-full space-y-1.5">
						<div v-if="props.label" class="text-xs text-ink-gray-5">
							{{ props.label }}
						</div>
						<button
							class="flex h-7 w-full items-center justify-between gap-2 rounded-4 bg-surface-gray-2 py-1 px-2 text-base transition-colors hover:bg-surface-gray-3 focus:ring-2 focus:ring-outline-gray-3"
						>
							<div class="flex flex-1 items-center gap-2 overflow-hidden truncate">
								<span v-if="measure.measure_name">
									{{ measure.measure_name }}
								</span>
								<span v-else class="text-ink-gray-4"> Select a column </span>
							</div>
						</button>
					</div>
				</template>

				<template #default="{ toggle: togglePopover }">
					<div
						class="relative mt-1 overflow-hidden rounded-6 bg-surface-base p-1.5 text-base shadow-2xl"
					>
						<template v-if="columnMeasure && !expressionMeasure">
							<span
								v-if="!shownAggregation"
								class="block px-1.5 py-0.5 text-p-xs text-ink-gray-5"
							>
								Select a Function
							</span>
							<div v-else class="mb-1 flex items-center">
								<Button class="!h-6 !w-6" @click.prevent.stop="resetAggregation">
									<template #icon>
										<ChevronLeft
											class="h-4 w-4 text-ink-gray-6"
											stroke-width="1.5"
										/>
									</template>
								</Button>
								<span class="block px-1.5 py-0.5 text-p-xs text-ink-gray-5">
									{{ getAggregationLabel(shownAggregation) }}
								</span>
							</div>
							<div class="flex max-h-[15rem] flex-col overflow-y-scroll">
								<template v-if="!shownAggregation">
									<div
										v-for="option in aggregationOptions"
										:key="option.value"
										class="flex h-7 flex-shrink-0 cursor-pointer items-center justify-between rounded-4 px-2.5 text-base hover:bg-surface-gray-2"
										@click.prevent.stop="pickAggregation(option.value)"
									>
										<span>{{ option.label }}</span>
										<span v-if="option.value === shownAggregation">
											<Check
												class="h-4 w-4 text-ink-gray-6"
												stroke-width="1.5"
											/>
										</span>
									</div>
								</template>

								<template v-else>
									<div class="sticky top-0 z-10 bg-surface-base space-y-1 p-1">
										<TextInput
											v-model="searchQuery"
											:placeholder="__('Search...')"
											autocomplete="off"
										/>
									</div>
									<div
										v-for="option in filteredColumnOptions"
										:key="option.value"
										class="flex h-7 flex-shrink-0 cursor-pointer items-center justify-between rounded-4 px-2.5 text-base hover:bg-surface-gray-2"
										@click.prevent.stop="
											() => {
												pickColumn(option)
												togglePopover()
											}
										"
									>
										<span>{{ option.label }}</span>
										<span v-if="option.value === columnMeasure.column_name">
											<Check
												class="h-4 w-4 text-ink-gray-6"
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
								:label="
									expressionMeasure
										? __('Edit Expression')
										: __('Custom Expression')
								"
								@click="openMeasureDialog(togglePopover)"
							>
								<template #prefix>
									<component
										:is="expressionMeasure ? Edit : Plus"
										class="h-4 w-4 text-ink-gray-6"
										stroke-width="1.5"
									/>
								</template>
							</Button>
						</div>
					</div>
				</template>
			</Popover>
		</div>
		<Popover v-if="measure.measure_name" side="bottom" align="end">
			<template #trigger>
				<Button>
					<template #icon>
						<Settings class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<template #default="{ close: closeSettings }">
				<div
					class="flex flex-col gap-2 p-2"
					:style="{ width: props.configWidth || CONFIG_WIDTH }"
				>
					<InlineFormControlLabel :label="__('Label')">
						<TextInput
							autocomplete="off"
							:modelValue="measure.measure_name"
							@update:modelValue="label = $event"
							@blur="measure.measure_name = label"
							@keydown.enter="measure.measure_name = label"
						/>
					</InlineFormControlLabel>

					<InlineFormControlLabel v-if="props.enableFormat" :label="__('Unit')">
						<FormControl
							type="select"
							:options="formatOptions"
							:modelValue="measure.format || ''"
							@update:modelValue="measure.format = $event || undefined"
						/>
					</InlineFormControlLabel>

					<InlineFormControlLabel
						v-if="props.enableFormat && measure.format === 'currency'"
						:label="__('Currency from')"
					>
						<FormControl
							type="select"
							:options="currencyColumnOptions"
							:modelValue="measure.currency_column || ''"
							@update:modelValue="measure.currency_column = $event || undefined"
						/>
					</InlineFormControlLabel>

					<slot name="config-fields" :close="closeSettings" />

					<div class="flex gap-1">
						<Button
							class="w-full"
							variant="outline"
							theme="red"
							iconLeft="lucide-x"
							@click="handleRemove"
						>
							Remove
						</Button>
					</div>
				</div>
			</template>
		</Popover>
		<Button v-else @click="emit('remove')">
			<template #icon>
				<XIcon class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
			</template>
		</Button>
	</div>
</template>
