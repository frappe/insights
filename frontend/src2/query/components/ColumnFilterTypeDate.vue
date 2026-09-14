<script setup lang="ts">
import { wheneverChanges } from '../../helpers'
import { __ } from '../../translation'
import dayjs from '../../helpers/dayjs'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import useSettings from '../../settings/settings'
import { FilterOperator, FilterValue, QueryResultColumn } from '../../types/query.types'
import DatePicker from './DatePicker.vue'

const props = defineProps<{ column: QueryResultColumn }>()
const filter = defineModel<{ operator: FilterOperator; value: FilterValue }>({
	type: Object,
	default: () => ({ operator: '=', value: [] }),
})

const currentSection = ref<'presets' | 'relative' | 'specific' | ''>('presets')
wheneverChanges(currentSection, () => {
	if (currentSection.value === 'presets') {
		filter.value = { operator: '=', value: [] }
	} else if (currentSection.value === 'relative') {
		filter.value = { operator: 'within', value: ['Last', 1, 'Day'] }
	} else if (currentSection.value === 'specific') {
		filter.value = { operator: '=', value: [] }
	} else {
		filter.value = { operator: '=', value: [] }
	}
})

const settings = useSettings()

const getValue = (date: Date) =>
	date.toLocaleDateString('en-US', {
		month: 'short',
		day: 'numeric',
	})
type Day = ReturnType<typeof dayjs>
const getRange = (start: Day, end: Day) => `${getValue(start.toDate())} - ${getValue(end.toDate())}`

const WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
function startOfWeek() {
	const weekStartsOn = WEEKDAYS.indexOf(settings.doc.week_starts_on || 'Monday')
	// dayjs counts days from Sunday, WEEKDAYS from Monday
	const today = dayjs()
	const dayOfWeek = (today.day() + 6) % 7
	return today.subtract((dayOfWeek - weekStartsOn + 7) % 7, 'day')
}

const predefinedRanges = computed(() => {
	const weekStart = startOfWeek()
	const fyStart = dayjs(settings.doc.fiscal_year_start || '04-01-1999')
	return [
		{ label: __('Today'), value: 'Day', description: getValue(new Date()) },
		{
			label: __('This Week'),
			value: 'Week',
			description: getRange(weekStart, weekStart.add(6, 'day')),
		},
		{
			label: __('This Month'),
			value: 'Month',
			description: getRange(dayjs().startOf('month'), dayjs().endOf('month')),
		},
		{
			label: __('This Quarter'),
			value: 'Quarter',
			description: getRange(dayjs().startOf('quarter'), dayjs().endOf('quarter')),
		},
		{
			label: __('This Year'),
			value: 'Year',
			description: getRange(dayjs().startOf('year'), dayjs().endOf('year')),
		},
		{
			label: __('This FY'),
			value: 'Fiscal Year',
			description: getRange(fyStart, fyStart.add(1, 'year').subtract(1, 'day')),
		},
		// last 7 days
		// last 30 days
		// last 90 days
		// last 3 months
		// last 6 months
		// last 12 months
		// last month
		// last year
		// month to date
		// year to date
		// all time
	]
})

function onPredefinedRangeInput(rangeValue: string) {
	filter.value = { operator: 'within', value: ['Current', rangeValue] }
}

function isRangeSelected(rangeValue: string) {
	if (!filter.value || !filter.value.value) return false
	const value = filter.value.value as string[]
	return filter.value.operator === 'within' && value[1] === rangeValue
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
		<div class="flex flex-col gap-1 pb-2">
			<div
				class="flex cursor-pointer items-center justify-between text-sm text-ink-gray-5 hover:underline"
				@click="currentSection = currentSection == 'presets' ? '' : 'presets'"
			>
				<span> Presets </span>
				<component
					:is="currentSection == 'presets' ? ChevronDown : ChevronRight"
					class="h-4 w-4"
					stroke-width="1.5"
				/>
			</div>
			<div v-if="currentSection == 'presets'">
				<div
					v-for="range in predefinedRanges"
					:key="range.value"
					class="-mx-1 flex cursor-pointer items-center justify-between gap-8 rounded-4 px-1 py-1"
					@click="onPredefinedRangeInput(range.value)"
					:class="
						isRangeSelected(range.value)
							? 'outline outline-gray-500'
							: 'hover:bg-surface-gray-2'
					"
				>
					<span>{{ range.label }}</span>
					<span class="text-sm text-ink-gray-5">{{ range.description }}</span>
				</div>
			</div>
		</div>

		<div>
			<div class="flex flex-col gap-1 py-2">
				<div
					class="flex cursor-pointer items-center justify-between text-sm text-ink-gray-5 hover:underline"
					@click="currentSection = currentSection == 'relative' ? '' : 'relative'"
				>
					<span> Relative Dates </span>
					<component
						:is="currentSection == 'relative' ? ChevronDown : ChevronRight"
						class="h-4 w-4"
						stroke-width="1.5"
					/>
				</div>
				<div
					v-if="currentSection == 'relative' && Array.isArray(filter.value)"
					class="flex flex-col gap-1 py-2"
				>
					<span>In Last...</span>
					<div class="flex gap-2">
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
		</div>

		<div class="">
			<div class="flex flex-col gap-2 pt-2">
				<div
					class="flex cursor-pointer items-center justify-between text-sm text-ink-gray-5 hover:underline"
					@click="currentSection = currentSection == 'specific' ? '' : 'specific'"
				>
					<span> Specific Dates </span>
					<component
						:is="currentSection == 'specific' ? ChevronDown : ChevronRight"
						class="h-4 w-4"
						stroke-width="1.5"
					/>
				</div>
				<DatePicker
					v-if="currentSection == 'specific' && Array.isArray(filter.value)"
					:modelValue="filter.value"
					@update:modelValue="onDatePickerInput"
				/>
			</div>
		</div>
	</div>
</template>
