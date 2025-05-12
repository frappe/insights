<template>
	<div class="flex w-[210px] select-none flex-col gap-2 bg-white text-base">
		<div class="flex items-center justify-between text-gray-700">
			<Button @click="prevMonth" icon="chevron-left" />
			<Button @dblclick="clearDates"> {{ formatMonth() }} </Button>
			<Button @click="nextMonth" icon="chevron-right" />
		</div>
		<div class="flex gap-2">
			<FormControl
				class="flex-1"
				placeholder="Enter date"
				v-model="fromDateTxt"
				autocomplete="off"
				@update:modelValue="selectDates(), selectCurrentMonthYear()"
			></FormControl>
			<FormControl
				v-if="range"
				class="flex-1"
				placeholder="Enter date"
				v-model="toDateTxt"
				autocomplete="off"
				@update:modelValue="selectDates(), selectCurrentMonthYear()"
			></FormControl>
		</div>
		<div class="tnum flex flex-col items-center justify-center text-base">
			<div class="grid w-full grid-cols-7">
				<div
					v-for="(d, i) in ['S', 'M', 'T', 'W', 'T', 'F', 'S']"
					:key="i"
					class="flex h-[30px] w-[30px] items-center justify-center text-sm text-gray-600"
				>
					{{ d }}
				</div>
				<template v-for="(week, i) in daysAsWeeks" :key="i">
					<div
						v-for="date in week"
						:key="toValue(date)"
						class="flex h-[30px] w-[30px] cursor-pointer items-center justify-center text-sm"
						:class="{
							'font-bold': toValue(date) === toValue(today),
							' rounded-l bg-gray-400 !font-medium':
								fromDateTxt && toValue(date) === toValue(fromDateTxt),
							' rounded-r bg-gray-400 !font-medium':
								toDateTxt && toValue(date) === toValue(toDateTxt),
							'bg-gray-100 font-medium text-gray-800': isInRange(date),
						}"
						@click="() => handleDateClick(date)"
					>
						{{ date.getDate() }}
					</div>
				</template>
			</div>
			<p v-if="range" class="mt-1 text-xs leading-4 text-gray-600">
				{{ description }}
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref } from 'vue'

const props = defineProps({
	range: {
		type: Boolean,
		default: true,
	},
})
const selectedDates = defineModel<string[]>({
	type: Array,
	default: () => [],
})

const today = new Date()

const currentYear = ref<number>(today.getFullYear())
const currentMonth = ref<number>(today.getMonth() + 1)
const fromDateTxt = ref<string>(selectedDates.value[0] || '')
const toDateTxt = ref<string>(selectedDates.value[1] || '')

onBeforeMount(() => {
	selectCurrentMonthYear()
})

function selectCurrentMonthYear() {
	const date = toDateTxt.value
		? new Date(toDateTxt.value)
		: fromDateTxt.value
		? new Date(fromDateTxt.value)
		: today
	currentYear.value = date.getFullYear()
	currentMonth.value = date.getMonth() + 1
}

const daysAsWeeks = computed(() => {
	const datesAsWeeks = []
	const _dates = dates.value.slice()
	while (_dates.length) {
		const week = _dates.splice(0, 7)
		datesAsWeeks.push(week)
	}
	return datesAsWeeks
})

const dates = computed(() => {
	if (!(currentYear.value && currentMonth.value)) {
		return []
	}
	const monthIndex = currentMonth.value - 1
	const year = currentYear.value

	const firstDayOfMonth = getDate(year, monthIndex, 1)
	const lastDayOfMonth = getDate(year, monthIndex + 1, 0)
	const leftPaddingCount = firstDayOfMonth.getDay()
	const rightPaddingCount = 6 - lastDayOfMonth.getDay()

	const leftPadding = getDatesAfter(firstDayOfMonth, -leftPaddingCount)
	const rightPadding = getDatesAfter(lastDayOfMonth, rightPaddingCount)
	const daysInMonth = getDaysInMonth(monthIndex, year)
	const datesInMonth = getDatesAfter(firstDayOfMonth, daysInMonth - 1)

	let _dates = [...leftPadding, firstDayOfMonth, ...datesInMonth, ...rightPadding]
	if (_dates.length < 42) {
		const lastDate = _dates.at(-1)
		if (lastDate) {
			const finalPadding = getDatesAfter(lastDate, 42 - _dates.length)
			_dates = _dates.concat(...finalPadding)
		}
	}
	return _dates
})

function getDatesAfter(firstDayOfMonth: Date, count: number) {
	let incrementer = 1
	if (count < 0) {
		incrementer = -1
		count = Math.abs(count)
	}
	let dates = []
	while (count) {
		firstDayOfMonth = getDate(
			firstDayOfMonth.getFullYear(),
			firstDayOfMonth.getMonth(),
			firstDayOfMonth.getDate() + incrementer
		)
		dates.push(firstDayOfMonth)
		count--
	}
	if (incrementer === -1) {
		return dates.reverse()
	}
	return dates
}

function getDaysInMonth(monthIndex: number, year: number) {
	let daysInMonthMap = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
	let daysInMonth = daysInMonthMap[monthIndex]
	if (monthIndex === 1 && isLeapYear(year)) {
		return 29
	}
	return daysInMonth
}

function isLeapYear(year: number) {
	if (year % 400 === 0) return true
	if (year % 100 === 0) return false
	if (year % 4 === 0) return true
	return false
}

function formatMonth() {
	const date = getDate(currentYear.value, currentMonth.value - 1, 1)
	return date.toLocaleString('en-US', {
		month: 'short',
		year: 'numeric',
	})
}

function formatDate(date: Date, options: { year?: boolean } = {}) {
	return date.toLocaleDateString('en-US', {
		day: 'numeric',
		month: 'short',
		year: options.year ? 'numeric' : undefined,
	})
}

function handleDateClick(date: Date) {
	if (!props.range) {
		fromDateTxt.value = toValue(date)
		selectDates()
		return
	}
	if (fromDateTxt.value && toDateTxt.value) {
		fromDateTxt.value = toValue(date)
		toDateTxt.value = ''
	} else if (fromDateTxt.value && !toDateTxt.value) {
		toDateTxt.value = toValue(date)
	} else {
		fromDateTxt.value = toValue(date)
	}
	swapDatesIfNecessary()
	selectDates()
}

function swapDatesIfNecessary() {
	if (!fromDateTxt.value || !toDateTxt.value) {
		return
	}
	let fromDate = getDate(fromDateTxt.value)
	let toDate = getDate(toDateTxt.value)
	if (fromDate > toDate) {
		let temp = fromDate
		fromDate = toDate
		toDate = temp
	}
	fromDateTxt.value = toValue(fromDate)
	toDateTxt.value = toValue(toDate)
}

function selectDates() {
	if (!props.range) {
		selectedDates.value = [fromDateTxt.value]
		return
	}
	if (!fromDateTxt.value && !toDateTxt.value) {
		selectedDates.value = []
		return
	}
	selectedDates.value = [fromDateTxt.value, toDateTxt.value]
}

function prevMonth() {
	changeMonth(-1)
}

function nextMonth() {
	changeMonth(1)
}

function changeMonth(adder: number) {
	currentMonth.value = currentMonth.value + adder
	if (currentMonth.value < 1) {
		currentMonth.value = 12
		currentYear.value = currentYear.value - 1
	}
	if (currentMonth.value > 12) {
		currentMonth.value = 1
		currentYear.value = currentYear.value + 1
	}
}

function isInRange(date: Date) {
	if (!fromDateTxt.value || !toDateTxt.value) {
		return false
	}
	return date >= getDate(fromDateTxt.value) && date <= getDate(toDateTxt.value)
}

function clearDates() {
	fromDateTxt.value = ''
	toDateTxt.value = ''
	selectCurrentMonthYear()
	selectDates()
}

function toValue(date: Date | string) {
	if (!date) {
		return ''
	}
	if (typeof date === 'string') {
		return date
	}

	// toISOString is buggy and reduces the day by one
	// this is because it considers the UTC timestamp
	// in order to circumvent that we need to use luxon/moment
	// but that refactor could take some time, so fixing the time difference
	// as suggested in this answer.
	// https://stackoverflow.com/a/16084846/3541205
	date.setHours(0, -date.getTimezoneOffset(), 0, 0)
	return date.toISOString().slice(0, 10)
}

function getDate(...args: any) {
	// @ts-ignore
	return new Date(...args)
}

const description = computed(() => {
	const fromDate = fromDateTxt.value ? getDate(fromDateTxt.value) : null
	const toDate = toDateTxt.value ? getDate(toDateTxt.value) : null

	const fromDateYear = fromDate?.getFullYear()
	const toDateYear = toDate?.getFullYear()

	const formatted = (date: Date) => formatDate(date, { year: fromDateYear !== toDateYear })

	if (fromDate && toDate && fromDate.getTime() === toDate.getTime()) {
		return `Equals: ${formatted(fromDate)}`
	}
	if (fromDate && toDate) {
		return `Between: ${formatted(fromDate)} and ${formatted(toDate)}`
	}
	if (fromDate) {
		return `Greater than: ${formatted(fromDate)}`
	}
	if (toDate) {
		return `Less than: ${formatted(toDate)}`
	}
	return ''
})
</script>
