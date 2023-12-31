<script setup>
import { formatNumber } from '@/utils'

const props = defineProps({
	value: { type: Number, required: true },
	prefix: { type: String, required: false, default: '' },
	suffix: { type: String, required: false, default: '' },
	decimals: { type: Number, required: false, default: 2 },
	minValue: { type: Number, required: true },
	maxValue: { type: Number, required: true },
	showInlineBarChart: { type: Boolean, required: false, default: false },
})
</script>

<template>
	<div class="flex items-center gap-2">
		<div class="tnum flex-1 flex-shrink-0 text-right">
			{{ prefix }}{{ formatNumber(value, decimals) }}{{ suffix }}
		</div>
		<div
			v-if="showInlineBarChart"
			class="flex overflow-hidden rounded-full"
			:class="minValue < 0 ? 'w-24' : 'w-20'"
		>
			<div v-if="minValue < 0" class="h-2 flex-1 bg-red-200">
				<div
					v-if="value < 0"
					class="float-right h-full bg-red-500"
					:style="{ width: `${(Math.abs(value) / maxValue) * 100}%` }"
				></div>
			</div>
			<div class="h-2 flex-1 bg-blue-200">
				<div
					v-if="value > 0"
					class="h-full bg-blue-500"
					:style="{ width: `${(value / maxValue) * 100}%` }"
				></div>
			</div>
		</div>
	</div>
</template>
