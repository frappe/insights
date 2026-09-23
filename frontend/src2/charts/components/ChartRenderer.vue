<script setup lang="ts">
import ChartView from '../ChartView.vue'
import BuilderDrillDown from '../drill/BuilderDrillDown.vue'
import type { ChartRead } from '../chart_view'

// The chart card an author gets: the same card every reader gets, with the
// author's drill in it. The card itself — the chrome, the acts row, the hover
// rule, expand — is `ChartView`, so there is one of each and not two.
//
// The drill is the whole difference. The owner's is the reader's plus "open as
// query", which reaches the workbook: a view surface mounts none of it, which is
// why this is a component of its own rather than a flag.
const props = defineProps<{
	chart?: ChartRead
	reading?: string
	hideMaximize?: boolean
	/** a host whose own action is open has taken the pointer out of the hover group */
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
