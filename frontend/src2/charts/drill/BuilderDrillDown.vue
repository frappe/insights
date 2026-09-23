<script setup lang="ts">
import { Button, toast } from 'frappe-ui'
import { SquareArrowOutUpRight } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { __ } from '../../translation'
import { workbookKey } from '../../workbook/workbook_key'
import ChartDrillDown from './ChartDrillDown.vue'
import type { DrillLevelData, DrillSubject } from './drill_stack'
import DrillRowsView from './DrillRowsView.vue'
import type { ChartSegmentClick } from './segment_click'

// The same drill, plus the one thing an author gets: a level added to the
// workbook as a query of its own.
//
// It is a component of its own rather than a flag on the drill because of what
// it imports. Adding a query is the workbook's, and the desk island draws
// charts without one — the same split `chart_preview` makes against
// `chart_view`. A view surface mounts `ViewDrillDown` and gets none of this.
const props = defineProps<{
	subject: DrillSubject
	clicked: ChartSegmentClick
}>()

const emit = defineEmits<{ close: [] }>()

// Two checks, one per owner. Only the authoring endpoint returns the cut
// pipeline, and only to a caller who may write what it was cut from. The
// client owns the other half: a workbook this user only reads is not one to
// add a query to.
const workbook = inject(workbookKey, null)
function openable(answer: DrillLevelData) {
	return Boolean(answer.operations?.length) && Boolean(workbook) && !workbook?.doc.read_only
}

// The rows level on screen, for as long as it is. Its answer is the one the
// reader's own filter, sort and find last asked for.
const $rows = ref<InstanceType<typeof DrillRowsView> | null>(null)

// A new query, which runs as its own author: it carries the level's cut, not the
// chart's declaration of whose rows it reads.
function addToWorkbook(first: DrillLevelData) {
	const answer = $rows.value?.rows.level ?? first
	const title = __('{0} — Drill Down', props.subject.title)
	confirmDialog({
		title: __('Open as Query'),
		message: __('“{0}” will be added to this workbook as a new query.', title),
		primaryActionLabel: __('Add Query'),
		onSuccess: () => {
			workbook?.addQuery({
				title,
				operations: answer.operations || [],
				use_live_connection: answer.use_live_connection,
			})
			// a filter on a query deeper than the chart's has no step in the new
			// query, so it holds more rows than the dialog showed
			if (answer.uncarried_filters?.length) {
				toast.warning(
					__(
						'The new query does not apply the dashboard filters: {0}',
						answer.uncarried_filters.join(', '),
					),
				)
			}
			emit('close')
		},
	})
}
</script>

<template>
	<ChartDrillDown :subject="props.subject" :clicked="props.clicked" @close="emit('close')">
		<template #actions="{ answer }">
			<Button
				v-if="openable(answer)"
				variant="ghost"
				:tooltip="__('Open as query')"
				@click="addToWorkbook(answer)"
			>
				<template #icon>
					<SquareArrowOutUpRight class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</template>
			</Button>
		</template>

		<!-- the rows are the server's, read as the chart and on the day its card
		     was, the same way a reader's are -->
		<template #rows="{ answer, levels, findTarget }">
			<DrillRowsView
				ref="$rows"
				:answer="answer"
				:levels="levels"
				:subject="props.subject"
				:find-target="findTarget"
			/>
		</template>
	</ChartDrillDown>
</template>
