<script setup lang="ts">
// PROTOTYPE — throwaway. An inline range calendar with a preset sidebar.
//
// frappe-ui's DateRangePicker cannot render inline: it is a PickerShell, so it
// always owns a trigger input and a popover of its own, and its CalendarPanel
// is not reachable from the package (`exports` stops at `frappe-ui`). So the
// grid below is CalendarPanel's markup and cell states, rebuilt at prototype
// depth, and the sidebar is the `actions` slot's idea placed next to it.

import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import { Button } from 'frappe-ui'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import type { FilterOperator, FilterValue } from '../types/query.types'
import { DATE_FORMAT, DATE_PRESETS, daySpan, resolveSpan } from './proto_filter'

const props = defineProps<{
	/** The range currently highlighted, as `YYYY-MM-DD`. */
	from?: string
	to?: string
	/** The preset whose row reads as active. */
	span?: string
}>()

const emit = defineEmits<{
	pick: [operator: FilterOperator, value: FilterValue]
	done: []
}>()

const WEEKDAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
const MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ')

const from = ref(props.from || '')
const to = ref(props.to || '')
const activeSpan = ref(props.span || '')
const hovered = ref<Dayjs | null>(null)

const anchor = ref(dayjs(from.value || undefined))
const year = computed(() => anchor.value.year())
const month = computed(() => anchor.value.month())

const weeks = computed(() => {
	const start = dayjs().year(year.value).month(month.value).date(1).startOf('week')
	const rows: Dayjs[][] = []
	let day = start
	for (let week = 0; week < 6; week++) {
		const row: Dayjs[] = []
		for (let index = 0; index < 7; index++) {
			row.push(day)
			day = day.add(1, 'day')
		}
		rows.push(row)
	}
	return rows
})

// While the end is still open the hovered cell previews the range, the way
// DateRangePicker's own grid does.
const previewEnd = computed(() => (from.value && !to.value ? hovered.value : null))

function cellState(day: Dayjs) {
	const start = from.value ? dayjs(from.value) : null
	const end = to.value ? dayjs(to.value) : null
	const isEdge = Boolean((start && day.isSame(start, 'day')) || (end && day.isSame(end, 'day')))
	let inRange = false
	if (start && end) {
		inRange = day.isAfter(start, 'day') && day.isBefore(end, 'day')
	} else if (start && previewEnd.value) {
		const [a, b] = previewEnd.value.isBefore(start)
			? [previewEnd.value, start]
			: [start, previewEnd.value]
		inRange = day.isAfter(a, 'day') && day.isBefore(b, 'day')
	}
	return {
		isEdge,
		inRange,
		inMonth: day.month() === month.value,
		isToday: day.isSame(dayjs(), 'day'),
	}
}

function cellClass(day: Dayjs) {
	const state = cellState(day)
	if (state.isEdge) {
		return [
			'rounded-4 bg-surface-gray-9 text-ink-base hover:bg-surface-gray-9',
			state.isToday ? 'font-semibold' : '',
		]
	}
	return [
		'rounded-4',
		state.inMonth ? 'text-ink-gray-8' : 'text-ink-gray-3',
		state.isToday ? 'font-semibold text-ink-gray-9' : '',
		state.inRange ? 'bg-surface-gray-3 hover:bg-surface-gray-3' : 'hover:bg-surface-gray-2',
	]
}

function pickPreset(preset: { label: string; span: string }) {
	const [start, end] = resolveSpan(preset.span)
	from.value = start
	to.value = end
	activeSpan.value = preset.span
	anchor.value = dayjs(start)
	emit('pick', 'within', { span: preset.span })
	emit('done')
}

// The first click names a day and applies it as a one-day window. The second
// extends it into a range and closes. A preset closes on its own click.
function pickDay(day: Dayjs) {
	const date = day.format(DATE_FORMAT)
	activeSpan.value = ''
	if (!from.value || to.value) {
		from.value = date
		to.value = ''
		emit('pick', 'within', daySpan(date))
		return
	}
	const [start, end] = dayjs(from.value).isAfter(day) ? [date, from.value] : [from.value, date]
	from.value = start
	to.value = end
	hovered.value = null
	emit('pick', 'between', [start, end])
	emit('done')
}
</script>

<template>
	<div class="flex divide-x divide-outline-gray-2">
		<aside aria-label="Date presets" class="flex w-32 shrink-0 flex-col gap-0.5 p-2">
			<Button
				v-for="preset in DATE_PRESETS"
				:key="preset.span"
				variant="ghost"
				size="sm"
				:label="preset.label"
				class="!justify-start"
				:class="activeSpan === preset.span ? '!bg-surface-gray-2' : ''"
				@click="pickPreset(preset)"
			/>
		</aside>

		<div class="select-none text-base text-ink-gray-9">
			<div class="flex items-center justify-between gap-1 p-2 pb-0">
				<span class="ps-1 text-sm font-medium text-ink-gray-7">
					{{ MONTHS[month] }} {{ year }}
				</span>
				<div class="flex items-center">
					<Button
						variant="ghost"
						label="Previous month"
						@click="anchor = anchor.subtract(1, 'month')"
					>
						<template #icon><ChevronLeft class="size-4" stroke-width="1.5" /></template>
					</Button>
					<Button
						variant="ghost"
						label="Next month"
						@click="anchor = anchor.add(1, 'month')"
					>
						<template #icon
							><ChevronRight class="size-4" stroke-width="1.5"
						/></template>
					</Button>
				</div>
			</div>
			<div class="p-2" role="grid" aria-label="Calendar dates" @mouseleave="hovered = null">
				<div
					class="mb-1 flex items-center gap-0.5 text-xs font-medium uppercase text-ink-gray-4"
				>
					<div
						v-for="(day, index) in WEEKDAYS"
						:key="index"
						class="flex size-7 items-center justify-center"
					>
						{{ day }}
					</div>
				</div>
				<div class="flex flex-col gap-0.5">
					<div
						v-for="(week, index) in weeks"
						:key="index"
						role="row"
						class="flex gap-0.5"
					>
						<button
							v-for="day in week"
							:key="day.format(DATE_FORMAT)"
							type="button"
							role="gridcell"
							class="flex size-7 cursor-pointer items-center justify-center text-sm transition-colors duration-100"
							:class="cellClass(day)"
							:aria-label="day.format(DATE_FORMAT)"
							@mouseenter="hovered = day"
							@click="pickDay(day)"
						>
							{{ day.date() }}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
