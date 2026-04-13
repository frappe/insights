<script setup lang="ts">
import { DatePicker } from 'frappe-ui'
import { computed, onMounted, watch } from 'vue'
import FormControl from '../../components/FormControl.vue'
import RadioGroup from '../../components/ui/Radio.vue'
import RadioGroupItem from '../../components/ui/RadioGroupItem.vue'
import { flattenOptions } from '../../helpers'
import { ColumnOption, GroupedColumnOption } from '../../types/query.types'
import { column } from '../helpers'
import { __ } from '../../translation'
import {
	cell_rules,
	color_scale,
	ConditionalOperator,
	date_rules,
	DateOperator,
	FormattingMode,
	rank_rules,
	RankOperator,
	text_rules,
	TextOperator,
} from './formatting_utils'
const format = defineModel<FormattingMode>({ required: true })
const props = defineProps<{
	columnOptions: ColumnOption[] | GroupedColumnOption[]
	formatMode: 'cell_rules' | 'color_scale'
}>()

onMounted(() => {
	if (format.value.column?.column_name) {
		return
	}
	const ruleType = getRuleTypeForColumn('')
	createNewFormat(ruleType, '')
})

watch(
	() => props.formatMode,
	(newMode) => {
		const currentColumn = format.value.column
		if (newMode === 'cell_rules') {
			const ruleType = getRuleTypeForColumn(currentColumn.column_name)
			createNewFormat(ruleType, currentColumn.column_name)
		} else {
			const newFormat: color_scale = {
				mode: 'color_scale',
				column: currentColumn,
				colorScale: colorScaleOptions[0].value,
				scaleScope: 'global',
				value: undefined,
			}
			format.value = newFormat
		}
	},
)

function getRuleTypeForColumn(
	columnName: string,
): 'cell_rules' | 'text_rules' | 'date_rules' | 'rank_rules' {
	const options = flattenOptions(props.columnOptions) as ColumnOption[]
	const col = options.find((c) => c.value === columnName)

	if (!col) return 'cell_rules'

	if (['Date', 'Datetime', 'Time'].includes(col.data_type)) {
		return 'date_rules'
	} else if (['String', 'Text'].includes(col.data_type)) {
		return 'text_rules'
	} else if (['Decimal', 'Number', 'Integer'].includes(col.data_type)) {
		return 'cell_rules'
	}

	return 'cell_rules'
}

function createNewFormat(ruleType: string, columnName: string) {
	switch (ruleType) {
		case 'text_rules':
			const textFormat: text_rules = {
				mode: 'text_rules',
				column: column(columnName),
				operator: textOperatorOptions[0].value,
				color: highlightColorOptions[0].value,
				value: '',
			}
			format.value = textFormat
			break
		case 'date_rules':
			const dateFormat: date_rules = {
				mode: 'date_rules',
				column: column(columnName),
				operator: dateOperatorOptions[0].value,
				color: highlightColorOptions[0].value,
				value: undefined,
			}
			format.value = dateFormat
			break
		case 'rank_rules':
			const rankFormat: rank_rules = {
				mode: 'rank_rules',
				column: column(columnName),
				operator: rankOperatorOptions[0].value,
				color: highlightColorOptions[0].value,
				value: 5,
			}
			format.value = rankFormat
			break
		default:
			const cellFormat: cell_rules = {
				mode: 'cell_rules',
				column: column(columnName),
				operator: operatorOptions[0].value,
				color: highlightColorOptions[0].value,
				value: 0,
			}
			format.value = cellFormat
	}
}

function onColumnChange(column_name: string) {
	if (props.formatMode === 'cell_rules') {
		const ruleType = getRuleTypeForColumn(column_name)
		createNewFormat(ruleType, column_name)
	} else {
		const newFormat: color_scale = {
			mode: 'color_scale',
			column: column(column_name),
			colorScale: colorScaleOptions[0].value,
			scaleScope: 'global',
			value: undefined,
		}
		format.value = newFormat
	}
}

const columnType = computed(() => {
	if (!props.columnOptions?.length) return
	if (!format.value.column.column_name) return
	const options = flattenOptions(props.columnOptions) as ColumnOption[]
	const col = options.find((c) => c.value === format.value.column.column_name)
	if (!col) return
	return col.data_type
})

const availableColumns = computed(() => {
	const options = flattenOptions(props.columnOptions) as ColumnOption[]

	// if color scale is selected, filter for numeric columns
	if (props.formatMode === 'color_scale') {
		return options.filter((option) =>
			['Decimal', 'Number', 'Integer'].includes(option.data_type),
		)
	}

	return options
})

const highlightColorOptions = [
	{ label: __('Red'), value: 'red' },
	{ label: __('Green'), value: 'green' },
	{ label: __('Amber'), value: 'amber' },
]

const operatorOptions = [
	{ label: __('equals'), value: '=' as ConditionalOperator },
	{ label: __('not equals'), value: '!=' as ConditionalOperator },
	{ label: __('greater than'), value: '>' as ConditionalOperator },
	{ label: __('greater than or equals'), value: '>=' as ConditionalOperator },
	{ label: __('less than'), value: '<' as ConditionalOperator },
	{ label: __('less than or equals'), value: '<=' as ConditionalOperator },
]

const textOperatorOptions = [
	{ label: __('contains'), value: 'contains' as TextOperator },
	{ label: __('does not contain'), value: 'not_contains' as TextOperator },
	{ label: __('starts with'), value: 'starts_with' as TextOperator },
	{ label: __('ends with'), value: 'ends_with' as TextOperator },
	{ label: __('equals'), value: 'equals_text' as TextOperator },
	{ label: __('does not equal'), value: 'not_equals_text' as TextOperator },
	{ label: __('is empty'), value: 'is_empty' as TextOperator },
	{ label: __('is not empty'), value: 'is_not_empty' as TextOperator },
]

const dateOperatorOptions = [
	{ label: __('is today'), value: 'is_today' as DateOperator },
	{ label: __('is yesterday'), value: 'is_yesterday' as DateOperator },
	{ label: __('is tomorrow'), value: 'is_tomorrow' as DateOperator },
	{ label: __('is this week'), value: 'is_this_week' as DateOperator },
	{ label: __('is last week'), value: 'is_last_week' as DateOperator },
	{ label: __('is this month'), value: 'is_this_month' as DateOperator },
	{ label: __('is last month'), value: 'is_last_month' as DateOperator },
	{ label: __('is this year'), value: 'is_this_year' as DateOperator },
	{ label: __('before date'), value: 'date_before' as DateOperator },
	{ label: __('after date'), value: 'date_after' as DateOperator },
	{ label: __('between dates'), value: 'date_between' as DateOperator },
]

const rankOperatorOptions = [
	{ label: __('Top N values'), value: 'top_n' as RankOperator },
	{ label: __('Bottom N values'), value: 'bottom_n' as RankOperator },
	{ label: __('Top N percent'), value: 'top_percent' as RankOperator },
	{ label: __('Bottom N percent'), value: 'bottom_percent' as RankOperator },
	{ label: __('Above average'), value: 'above_average' as RankOperator },
	{ label: __('Below average'), value: 'below_average' as RankOperator },
]

const colorScaleOptions = [
	{
		label: __('Red-Green'),
		value: 'Red-Green',
	},
	{
		label: __('Green-Red'),
		value: 'Green-Red',
	},
]

// filter out
const ruleTypeOptions = computed(() => {
	const options = []

	if (['Decimal', 'Number', 'Integer'].includes(columnType.value || '')) {
		options.push(
			{ label: __('Value Rules'), value: 'cell_rules' },
			{ label: __('Ranking Rules'), value: 'rank_rules' },
		)
	}

	if (['String', 'Text'].includes(columnType.value || '')) {
		options.push({ label: __('Text Rules'), value: 'text_rules' })
	}

	if (['Date', 'Datetime', 'Time'].includes(columnType.value || '')) {
		options.push({ label: __('Date Rules'), value: 'date_rules' })
	}

	return options
})

function onRuleTypeChange(newRuleType: string) {
	createNewFormat(newRuleType, format.value.column.column_name)
}

function onOperatorChange(operator: any) {
	if (format.value.mode === 'cell_rules') {
		;(format.value as cell_rules).operator = operator
	} else if (format.value.mode === 'text_rules') {
		;(format.value as text_rules).operator = operator
	} else if (format.value.mode === 'date_rules') {
		;(format.value as date_rules).operator = operator
	} else if (format.value.mode === 'rank_rules') {
		;(format.value as rank_rules).operator = operator
	}
}

function onColorScaleChange(newColor: string) {
	if (props.formatMode === 'color_scale' && format.value.mode === 'color_scale') {
		format.value.colorScale = newColor
	}
}

function onScaleScopeChange(newScope: 'global' | 'local') {
	if (props.formatMode === 'color_scale' && format.value.mode === 'color_scale') {
		format.value.scaleScope = newScope
	}
}

function onHighlightColorChange(newColor: string) {
	if (format.value.mode === 'cell_rules') {
		;(format.value as cell_rules).color = newColor
	} else if (format.value.mode === 'text_rules') {
		;(format.value as text_rules).color = newColor
	} else if (format.value.mode === 'date_rules') {
		;(format.value as date_rules).color = newColor
	} else if (format.value.mode === 'rank_rules') {
		;(format.value as rank_rules).color = newColor
	}
}

const isValueRule = computed(() => format.value.mode === 'cell_rules')
const isTextRule = computed(() => format.value.mode === 'text_rules')
const isDateRule = computed(() => format.value.mode === 'date_rules')
const isRankRule = computed(() => format.value.mode === 'rank_rules')

const currentColor = computed(() => {
	if (format.value.mode === 'cell_rules') {
		return (format.value as cell_rules).color
	} else if (format.value.mode === 'text_rules') {
		return (format.value as text_rules).color
	} else if (format.value.mode === 'date_rules') {
		return (format.value as date_rules).color
	} else if (format.value.mode === 'rank_rules') {
		return (format.value as rank_rules).color
	}
	return ''
})

// can use better naming
const isTextValueRule = computed(() => {
	if (!isTextRule.value) return false
	const op = (format.value as text_rules).operator
	return !['is_empty', 'is_not_empty'].includes(op)
})

const isDateValueRule = computed(() => {
	if (!isDateRule.value) return false
	const op = (format.value as date_rules).operator
	return ['date_before', 'date_after', 'date_between'].includes(op)
})

const isRankValueRule = computed(() => {
	if (!isRankRule.value) return false
	const op = (format.value as rank_rules).operator
	return ['top_n', 'bottom_n', 'top_percent', 'bottom_percent'].includes(op)
})

const isInvalidColumn = computed(() => {
	return !!(
		format.value.column.column_name &&
		!availableColumns.value.find((col) => col.value === format.value.column.column_name)
	)
})
</script>

<template>
	<div class="flex flex-col gap-1.5 relative">
		<Autocomplete
			:label="'Column'"
			:placeholder="__('Column')"
			:modelValue="format.column?.column_name"
			:options="availableColumns"
			@update:modelValue="onColumnChange(typeof $event === 'string' ? $event : $event?.value)"
		/>
		<p v-if="isInvalidColumn" class="text-xs text-red-500">Invalid Column</p>
	</div>

	<template v-if="!isInvalidColumn">
		<div v-if="props.formatMode === 'color_scale'" class="w-full flex flex-col gap-4">
			<div>
				<h3 class="text-sm text-gray-600 mb-3">Color</h3>
				<RadioGroup
					name="color-scale"
					:modelValue="(format as color_scale).colorScale"
					@update:modelValue="onColorScaleChange($event)"
				>
					<RadioGroupItem value="Red-Green" class="[&_label]:w-full">
						<div class="flex items-center justify-between gap-2 w-full">
							<span class="text-sm">Red to Green</span>
							<div class="flex h-2 w-32">
								<div class="w-1/2 bg-red-400"></div>
								<div class="w-1/2 bg-red-300"></div>
								<div class="w-1/2 bg-green-300"></div>
								<div class="w-1/2 bg-green-500"></div>
							</div>
						</div>
					</RadioGroupItem>
					<RadioGroupItem value="Green-Red" class="[&_label]:w-full">
						<div class="flex items-center justify-between gap-2 w-full">
							<span class="text-sm">Green to Red</span>
							<div class="flex h-2 w-32">
								<div class="w-1/2 bg-green-500"></div>
								<div class="w-1/2 bg-green-300"></div>
								<div class="w-1/2 bg-red-300"></div>
								<div class="w-1/2 bg-red-400"></div>
							</div>
						</div>
					</RadioGroupItem>
				</RadioGroup>
			</div>

			<div>
				<div class="flex items-center gap-2 mb-3">
					<h3 class="text-sm text-gray-600">Scale Scope</h3>
				</div>
				<RadioGroup
					name="scale-scope"
					:modelValue="(format as color_scale).scaleScope || 'global'"
					@update:modelValue="onScaleScopeChange($event)"
				>
					<RadioGroupItem value="global" class="[&_label]:w-full">
						<div class="flex flex-col gap-0.5">
							<span class="text-sm font-medium">Global</span>
							<span class="text-xs text-gray-500"
								>Compare across all formatted columns</span
							>
						</div>
					</RadioGroupItem>
					<RadioGroupItem value="local" class="[&_label]:w-full">
						<div class="flex flex-col gap-0.5">
							<span class="text-sm font-medium">Local</span>
							<span class="text-xs text-gray-500"
								>Compare within each column independently</span
							>
						</div>
					</RadioGroupItem>
				</RadioGroup>
			</div>
		</div>

		<div v-else class="flex flex-col gap-3">
			<template v-if="ruleTypeOptions.length > 1">
				<FormControl
					type="select"
					:label="'Rule Type'"
					:placeholder="__('Rule Type')"
					:modelValue="format.mode"
					:options="ruleTypeOptions"
					@update:modelValue="onRuleTypeChange($event)"
				/>
			</template>

			<template v-if="isValueRule">
				<FormControl
					type="select"
					:label="'Condition'"
					:placeholder="__('Operator')"
					:modelValue="(format as cell_rules).operator"
					:options="operatorOptions"
					@update:modelValue="onOperatorChange($event)"
				/>
				<FormControl
					type="number"
					:label="'Compare to'"
					:modelValue="(format as cell_rules).value"
					:placeholder="__('Value')"
					@update:modelValue="format.value = Number($event)"
				/>
			</template>

			<template v-if="isTextRule">
				<FormControl
					type="select"
					:label="__('Condition')"
					:modelValue="(format as text_rules).operator"
					:options="textOperatorOptions"
					@update:modelValue="onOperatorChange($event)"
				/>
				<template v-if="isTextValueRule">
					<FormControl
						type="text"
						:label="'Text Value'"
						:modelValue="(format as text_rules).value"
						:placeholder="__('Enter text')"
						@update:modelValue="format.value = $event"
					/>
				</template>
			</template>

			<template v-if="isDateRule">
				<FormControl
					type="select"
					:label="__('Condition')"
					:modelValue="(format as date_rules).operator"
					:options="dateOperatorOptions"
					@update:modelValue="onOperatorChange($event)"
				/>
				<template v-if="isDateValueRule">
					<h3 class="text-sm text-gray-600">Date Value</h3>
					<template v-if="(format as date_rules).operator === 'date_between'">
						<!-- todo: find a proper fix for datepicker v-model -->
						<DatePicker
							v-model="(format as date_rules).value as string"
							:range="true"
						/>
					</template>
					<template v-else>
						<DatePicker
							v-model="(format as date_rules).value as string"
							:range="false"
						/>
					</template>
				</template>
			</template>

			<template v-if="isRankRule">
				<FormControl
					type="select"
					:placeholder="__('Ranking Condition')"
					:label="'Rule'"
					:modelValue="(format as rank_rules).operator"
					:options="rankOperatorOptions"
					@update:modelValue="onOperatorChange($event)"
				/>
				<template v-if="isRankValueRule">
					<FormControl
						:label="'value'"
						type="number"
						:modelValue="(format as rank_rules).value"
						:placeholder="
							(format as rank_rules).operator?.includes('percent')
								? 'Percentage (1-100)'
								: 'Number of items'
						"
						@update:modelValue="format.value = Number($event)"
					/>
				</template>
			</template>

			<FormControl
				type="select"
				:label="'Color'"
				:placeholder="__('Color')"
				:modelValue="currentColor"
				:options="highlightColorOptions"
				@update:modelValue="onHighlightColorChange($event)"
			/>
		</div>
	</template>
</template>
