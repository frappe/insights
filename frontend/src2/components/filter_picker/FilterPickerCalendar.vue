<script setup lang="ts">
// The calendar an operator's value stage opens under the list: a range for
// `between`, one day for the rest. It holds no selection of its own — the
// highlight is read off the input, and a click writes the days back into it.
// `select` fires on every click, so re-picking the day already in the input
// still writes, where `update:modelValue` would go quiet.
import type { DateRangeValue } from 'frappe-ui'
import { DateCalendar, DateRangeCalendar } from 'frappe-ui/experimental'
import { computed } from 'vue'
import { calendarText, calendarValue } from './filter_picker'

const props = defineProps<{
	mode: 'range' | 'day'
	/** what the input reads */
	text: string
}>()

const emit = defineEmits<{ write: [text: string] }>()

const value = computed(() => calendarValue(props.mode, props.text))
const range = computed<DateRangeValue>(() => (Array.isArray(value.value) ? value.value : ['', '']))
const day = computed(() => (Array.isArray(value.value) ? '' : value.value))
</script>

<template>
	<!-- the picker's caret lives in the combobox input; a day click must not take it.
	     No Today button: the picker's own list already carries Today. -->
	<div class="filter-picker-calendar" @mousedown.prevent>
		<DateRangeCalendar
			v-if="mode === 'range'"
			:model-value="range"
			today-label=""
			@select="emit('write', calendarText($event))"
		/>
		<DateCalendar
			v-else
			:model-value="day"
			today-label=""
			@select="emit('write', calendarText($event))"
		/>
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
