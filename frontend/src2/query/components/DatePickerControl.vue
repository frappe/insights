<script setup lang="ts">
import { Calendar } from 'lucide-vue-next'
import { computed } from 'vue'
import DatePicker from './DatePicker.vue'

const props = defineProps({
	placeholder: {
		type: String,
		default: 'Select Date',
	},
	range: {
		type: Boolean,
		default: false,
	},
})
const dates = defineModel<string[]>({
	default: () => [],
	required: true,
})

const formatDate = (dates: string | string[] | Date | Date[]) => {
	const _dates: Date[] = []
	if (typeof dates === 'string') {
		_dates.push(new Date(dates))
	} else if (Array.isArray(dates) && dates.every((date) => typeof date === 'string')) {
		_dates.push(new Date(dates[0]))
		_dates.push(new Date(dates[1]))
	} else if (dates instanceof Date) {
		_dates.push(dates)
	} else if (Array.isArray(dates) && dates.every((date) => date instanceof Date)) {
		_dates.push(dates[0] as Date)
		_dates.push(dates[1] as Date)
	}

	// if year is same, show only month and day
	const [start, end] = _dates
	if (start && !end) {
		return start.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: start.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
		})
	}
	if (start && end) {
		return `${start.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: start.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
		})} - ${end.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			year: end.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
		})}`
	}
	return ''
}

const areAllDatesValid = computed(() => dates.value.length && dates.value.every((date) => date))
const displayDate = computed(() => {
	if (areAllDatesValid.value) {
		return props.range ? formatDate(dates.value) : formatDate(dates.value[0])
	}
	return props.placeholder
})
</script>

<template>
	<Popover placement="bottom-start">
		<template #target="{ togglePopover }">
			<Button
				class="w-full items-center !justify-start overflow-hidden"
				@click="togglePopover"
			>
				<template #prefix>
					<Calendar class="h-4 w-4 flex-shrink-0 text-gray-600" stroke-width="1.5" />
				</template>
				<span
					class="truncate"
					:class="areAllDatesValid ? 'text-gray-900' : 'text-gray-600'"
				>
					{{ displayDate }}
				</span>
			</Button>
		</template>
		<template #body-main>
			<div class="flex p-2">
				<DatePicker v-model="dates" :range="props.range"></DatePicker>
			</div>
		</template>
	</Popover>
</template>
