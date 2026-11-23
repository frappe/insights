<script setup lang="ts">
import ChartView from '../ChartView.vue'
import BuilderDrillDown from '../drill/BuilderDrillDown.vue'
import type { ChartRead } from '../chart_view'

// The author's drill adds "open as query", which needs the workbook. A View
// must not import that code, so this is a separate component and not a flag.
const props = defineProps<{
	chart?: ChartRead
	reading?: string
	hideMaximize?: boolean
	actionsRevealed?: boolean
	/** Whether the reader narrowed these rows, and can take that back. */
	filtered?: boolean
}>()

const emit = defineEmits<{
	resetFilters: []
}>()
</script>

<template>
	<ChartView
		:chart="props.chart"
		:reading="props.reading"
		:hide-maximize="props.hideMaximize"
		:actions-revealed="props.actionsRevealed"
		:filtered="props.filtered"
		:readonly="false"
		@reset-filters="emit('resetFilters')"
	>
		<template v-if="$slots.actions" #actions="{ expanded }">
			<slot name="actions" :expanded="expanded" />
		</template>
		<template v-if="$slots.hoverActions" #hoverActions>
			<slot name="hoverActions" />
		</template>

		<!-- `v-if` unmounts it on close, so every drill starts from an empty stack -->
		<template #drill="{ clicked, close }">
			<BuilderDrillDown
				v-if="clicked && props.chart"
				:subject="props.chart.drillSubject"
				:clicked="clicked"
				@close="close()"
			/>
		</template>
	</ChartView>
</template>
