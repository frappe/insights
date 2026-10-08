<script setup lang="ts">
import { computed } from 'vue'

export type StackedBarSegment = {
	key: string
	value: number
	class: string
	tooltip?: string
}

const props = withDefaults(
	defineProps<{
		segments: StackedBarSegment[]
		max?: number
		size?: 'sm' | 'md' | 'lg'
	}>(),
	{ size: 'md' },
)

const scale = computed(() => {
	const total = props.segments.reduce((sum, segment) => sum + segment.value, 0)
	return Math.max(props.max ?? total, total, 1)
})

const heightClass = computed(() => ({ sm: 'h-1.5', md: 'h-2', lg: 'h-3' })[props.size])
</script>

<template>
	<div class="flex w-full overflow-hidden rounded-7 bg-surface-gray-2" :class="heightClass">
		<Tooltip
			v-for="segment in segments.filter((s) => s.value > 0)"
			:key="segment.key"
			:text="segment.tooltip"
			:disabled="!segment.tooltip"
		>
			<div
				class="h-full min-w-[2px] shrink-0 border-r border-outline-base last:border-r-0"
				:class="segment.class"
				:style="{ width: `${(segment.value / scale) * 100}%` }"
			></div>
		</Tooltip>
	</div>
</template>
