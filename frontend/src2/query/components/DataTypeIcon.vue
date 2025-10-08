<script setup lang="ts">
import {
	Baseline,
	Braces,
	Brackets,
	Calendar,
	CalendarClock,
	Clock,
	Hash,
	ShieldQuestion,
	Type,
} from 'lucide-vue-next'
import { computed } from 'vue'
import { ColumnDataType } from '../../types/query.types'

const props = defineProps<{ columnType: ColumnDataType }>()
const icon = computed(() => {
	switch (props.columnType) {
		case 'Integer':
		case 'Decimal':
			return Hash
		case 'Date':
			return Calendar
		case 'Datetime':
			return CalendarClock
		case 'Time':
			return Clock
		case 'Text':
			return Type
		case 'JSON':
			return Braces
		case 'Array':
			return Brackets
		case 'String':
			return Baseline
		case 'Auto':
			return Baseline
		default:
			return ShieldQuestion
	}
})
</script>

<template>
	<component :is="icon" class="h-4 w-4 text-gray-700" stroke-width="1.5" />
</template>
