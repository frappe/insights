<script setup lang="ts">
// The calendar an operator's value stage opens under the list: a range for
// `between`, one day for the rest. It holds no selection of its own — the
// highlight is read off the input, and a click writes the days back into it.
import { CalendarPanel } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import dayjs from '../../helpers/dayjs'
import { calendarText, calendarValue } from './filter_picker'

const props = defineProps<{
	mode: 'range' | 'day'
	/** what the input reads */
	text: string
}>()

const emit = defineEmits<{ write: [text: string] }>()

/** an array binding is what puts CalendarPanel in range mode */
const value = computed(() => calendarValue(props.mode, props.text))

const currentYear = ref(dayjs().year())
const currentMonth = ref(dayjs().month())

// a date typed into the input is worth nothing if the month holding it is not
// the month on screen
watch(
	() => (Array.isArray(value.value) ? value.value[0] : value.value),
	(day) => {
		const parsed = dayjs(day)
		if (!day || !parsed.isValid()) return
		currentYear.value = parsed.year()
		currentMonth.value = parsed.month()
	},
	{ immediate: true },
)
</script>

<template>
	<!-- the picker's caret lives in the combobox input; a day click must not take it -->
	<div class="filter-picker-calendar">
		<CalendarPanel
			v-model:current-year="currentYear"
			v-model:current-month="currentMonth"
			:model-value="value"
			@mousedown.prevent
			@update:model-value="emit('write', calendarText($event))"
		/>
	</div>
</template>

<style scoped>
/* CalendarPanel sizes its cells; the panel is as wide as the list, so the grid
   is stretched to fill it and the header is pulled back together. */
.filter-picker-calendar :deep(.size-7) {
	width: auto;
	flex: 1 1 0%;
}
.filter-picker-calendar :deep(.justify-between) {
	justify-content: flex-start;
}
</style>
