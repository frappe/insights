<script setup lang="ts">
// The calendar an operator's value stage opens under the list: a range for
// `between`, one day for the rest. It holds no selection of its own — the
// highlight is read off the input, and a click writes the days back into it.
// `select` fires on every click, so re-picking the day already in the input
// still writes, where `update:modelValue` would go quiet.
//
// With `withTime` each day has a time of day beside it, in the same input: a
// click keeps the times written there, and a time field rewrites only its time.
import type { DateRangeValue } from 'frappe-ui'
import { TextInput } from 'frappe-ui'
import { DateCalendar, DateRangeCalendar } from 'frappe-ui/experimental'
import { computed } from 'vue'
import session from '../../session'
import { __ } from '../../translation'
import {
	calendarText,
	calendarValue,
	timedRangeOf,
	timedRangeText,
	type TimedRange,
} from './filter_picker'

const props = defineProps<{
	mode: 'range' | 'day'
	/** what the input reads */
	text: string
	withTime?: boolean
}>()

const emit = defineEmits<{ write: [text: string] }>()

const timed = computed(() => timedRangeOf(props.text))
const value = computed(() =>
	props.withTime
		? props.mode === 'range'
			? ([timed.value.from, timed.value.to] as [string, string])
			: timed.value.from
		: calendarValue(props.mode, props.text),
)
const range = computed<DateRangeValue>(() => (Array.isArray(value.value) ? value.value : ['', '']))
const day = computed(() => (Array.isArray(value.value) ? '' : value.value))

function onSelect(picked: string | string[] | undefined) {
	if (!props.withTime) return emit('write', calendarText(picked))
	const [from, to] = Array.isArray(picked) ? picked : [picked || '', '']
	write({ from: from || '', to: to || '' })
}

function write(change: Partial<TimedRange>) {
	emit('write', timedRangeText({ ...timed.value, ...change }, props.mode))
}
</script>

<template>
	<!-- the picker's caret lives in the combobox input; a day click must not take it.
	     No Today button: the picker's own list already includes Today. -->
	<div class="filter-picker-calendar" @mousedown.prevent>
		<DateRangeCalendar
			v-if="mode === 'range'"
			:model-value="range"
			today-label=""
			@select="onSelect"
		/>
		<DateCalendar v-else :model-value="day" today-label="" @select="onSelect" />
	</div>
	<!-- outside the mousedown guard: a time field takes the caret to be typed in -->
	<div v-if="withTime" class="flex flex-wrap gap-2 border-t border-outline-gray-1 p-2">
		<label class="flex flex-1 flex-col gap-1 text-xs text-ink-gray-5">
			{{ mode === 'range' ? __('From') : __('At') }}
			<TextInput
				type="time"
				size="sm"
				:disabled="!timed.from"
				:model-value="timed.fromTime"
				@update:model-value="$event && write({ fromTime: $event })"
			/>
		</label>
		<label v-if="mode === 'range'" class="flex flex-1 flex-col gap-1 text-xs text-ink-gray-5">
			{{ __('To') }}
			<TextInput
				type="time"
				size="sm"
				:disabled="!timed.to"
				:model-value="timed.toTime"
				@update:model-value="$event && write({ toTime: $event })"
			/>
		</label>
		<!-- the values are stored in the site's zone and shown as stored; a reader
		     in another zone has to know the clock they are reading -->
		<p v-if="session.site.time_zone" class="w-full text-xs text-ink-gray-5">
			{{ __('Times in {0}', session.site.time_zone) }}
		</p>
	</div>
</template>

<style scoped>
/* The range calendar's root is a flex row, so the panel inside it is sized from
   its content and the stretched cells inflate that content past the list's
   width. Both are made to fill instead. */
.filter-picker-calendar :deep(> *) {
	width: 100%;
}
.filter-picker-calendar :deep(> * > *) {
	min-width: 0;
	flex: 1 1 0%;
}
/* The calendar sizes its cells; the panel is as wide as the list, so the grid
   is stretched to fill it and the header is pulled back together. */
.filter-picker-calendar :deep(.size-7) {
	width: auto;
	flex: 1 1 0%;
}
.filter-picker-calendar :deep(.justify-between) {
	justify-content: flex-start;
}
</style>
