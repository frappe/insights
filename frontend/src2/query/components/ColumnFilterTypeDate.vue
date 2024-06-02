<script setup lang="ts">
import Checkbox from '@/components/Controls/Checkbox.vue'
import dayjs from '@/utils/dayjs'
import { ref } from 'vue'
import DatePicker from './DatePicker.vue'

const props = defineProps<{ column: QueryResultColumn }>()
const filter = defineModel<{ operator: FilterOperator; value: FilterValue }>({
	type: Object,
	default: () => ({ operator: '=', value: [] }),
})

const showDatePicker = ref(false)

const getValue = (date: Date) =>
	date.toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
	})
const todayValue = getValue(new Date())
const [weekStart, weekEnd] = [dayjs().startOf('week').toDate(), dayjs().endOf('week').toDate()]
const [monthStart, monthEnd] = [dayjs().startOf('month').toDate(), dayjs().endOf('month').toDate()]
const [qtrStart, qtrEnd] = [dayjs().startOf('quarter').toDate(), dayjs().endOf('quarter').toDate()]
const [yearStart, yearEnd] = [dayjs().startOf('year').toDate(), dayjs().endOf('year').toDate()]

const thisWeekValue = `${getValue(weekStart)} - ${getValue(weekEnd)}`
const thisMonthValue = `${getValue(monthStart)} - ${getValue(monthEnd)}`
const thisQuarterValue = `${getValue(qtrStart)} - ${getValue(qtrEnd)}`
const thisYearValue = `${getValue(yearStart)} - ${getValue(yearEnd)}`

const predefinedRanges = [
	{ label: 'Today', value: 'Day', description: todayValue },
	{ label: 'This Week', value: 'Week', description: thisWeekValue },
	{ label: 'This Month', value: 'Month', description: thisMonthValue },
	{ label: 'This Quarter', value: 'Quarter', description: thisQuarterValue },
	{ label: 'This Year', value: 'Year', description: thisYearValue },
]

function onPredefinedRangeInput(rangeValue: string) {
	withinLast.value = false
	showDatePicker.value = false
	filter.value = { operator: 'within', value: ['Current', rangeValue] }
}

function isRangeSelected(rangeValue: string) {
	if (!filter.value || !filter.value.value) return false
	const value = filter.value.value as string[]
	return filter.value.operator === 'within' && value[1] === rangeValue
}

const withinLast = ref(false)
function onWithinLastCheck(checked: boolean) {
	withinLast.value = checked
	showDatePicker.value = false
	if (checked) {
		filter.value = { operator: 'within', value: ['Last', 1, 'Day'] }
	} else {
		filter.value = { operator: '=', value: [] }
	}
}

function onSpecificDateCheck(checked: boolean) {
	withinLast.value = false
	showDatePicker.value = checked
	filter.value = { operator: '=', value: [] }
}

function onDatePickerInput(value: string[]) {
	// if both dates are same, set operator to '='
	// if only first date is present, set operator to '>'
	// if only second date is present, set operator to '<'
	// if both dates are present, set operator to 'between'
	filter.value.value = value
	if (value[0] === value[1]) {
		filter.value.operator = '='
	} else if (value[0] && !value[1]) {
		filter.value.operator = '>='
	} else if (!value[0] && value[1]) {
		filter.value.operator = '<='
	} else if (value[0] && value[1]) {
		filter.value.operator = 'between'
	} else {
		filter.value.operator = '='
	}
}
</script>

<template>
	<div class="flex w-[210px] flex-col divide-y text-base">
		<div class="flex flex-col gap-0.5 pb-2">
			<!-- predefined ranges -->
			<div
				v-for="range in predefinedRanges"
				:key="range.value"
				class="-mx-1 flex cursor-pointer items-center justify-between gap-8 rounded px-1 py-1"
				@click="onPredefinedRangeInput(range.value)"
				:class="
					isRangeSelected(range.value) ? 'outline outline-gray-500' : 'hover:bg-gray-100'
				"
			>
				<span>{{ range.label }}</span>
				<span class="text-sm text-gray-600">{{ range.description }}</span>
			</div>
		</div>

		<div class="py-3">
			<div class="flex flex-col gap-2">
				<Checkbox
					label="In Last..."
					:modelValue="withinLast"
					@update:modelValue="onWithinLastCheck"
				/>
				<div v-if="withinLast && Array.isArray(filter.value)" class="flex gap-2">
					<div class="flex-1">
						<FormControl
							type="number"
							autocomplete="off"
							:min="1"
							:max="100"
							:modelValue="filter.value[1]"
							@update:modelValue="filter.value[1] = $event"
						/>
					</div>
					<div class="flex-[2]">
						<FormControl
							type="select"
							autocomplete="off"
							:options="['Day', 'Week', 'Month', 'Quarter', 'Year']"
							:modelValue="filter.value[2]"
							@update:modelValue="filter.value[2] = $event"
						/>
					</div>
				</div>
			</div>
		</div>

		<div class="pt-3">
			<div class="flex flex-col gap-3">
				<Checkbox
					label="Specific Dates..."
					:modelValue="showDatePicker"
					@update:modelValue="onSpecificDateCheck"
				/>
				<DatePicker
					v-if="showDatePicker"
					:modelValue="(filter.value as string[])"
					@update:modelValue="onDatePickerInput"
				/>
			</div>
		</div>
	</div>
</template>
