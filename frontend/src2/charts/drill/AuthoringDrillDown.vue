<script setup lang="ts">
import { Button } from 'frappe-ui'
import { SquareArrowOutUpRight } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { __ } from '../../translation'
import type { AdhocFilters } from '../../types/query.types'
import { workbookKey } from '../../workbook/workbook_key'
import ChartDrillDown from './ChartDrillDown.vue'
import DrillQuery from './DrillQuery.vue'
import type { DrillLevelData, DrillSubject } from './drill_stack'
import type { ChartSegmentClick } from './segment_click'

// The same drill, plus the one thing an author gets: the level, continued in the
// full builder.
//
// It is a component of its own rather than a flag on the drill because of what
// it imports. A query editor is the whole builder, and the desk island draws
// charts without any of it — the same split `chart_preview` makes against
// `chart_read`. A reading surface mounts `ChartDrillDown` and gets none of this.
const props = defineProps<{
	subject: DrillSubject
	clicked: ChartSegmentClick
	/** what the surface's own filters narrowed to, which the slice does not carry */
	adhocFilters?: AdhocFilters
}>()

const emit = defineEmits<{ close: [] }>()

// Two halves to the gate, each asserted by whoever owns it. The server hands
// back the sliced pipeline through the authoring door alone, so a level that
// carries one is a level an author is reading. The client owns the other half:
// a workbook this user only reads is not one to open a query editor in.
const workbook = inject(workbookKey, null)
function openable(level: DrillLevelData) {
	return Boolean(level.operations?.length) && !workbook?.doc.read_only
}

const lifted = ref<DrillLevelData>()
</script>

<template>
	<ChartDrillDown :subject="props.subject" :clicked="props.clicked" @close="emit('close')">
		<template #actions="{ level }">
			<Button v-if="openable(level)" :label="__('Open as query')" @click="lifted = level">
				<template #prefix>
					<SquareArrowOutUpRight class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</template>
			</Button>
		</template>
	</ChartDrillDown>

	<!-- over the drill rather than in place of it, so closing the query returns
	     the author to the path they lifted it out of -->
	<DrillQuery
		v-if="lifted"
		:level="lifted"
		:title="props.subject.title"
		:adhoc-filters="props.adhocFilters"
		@closed="lifted = undefined"
	/>
</template>
