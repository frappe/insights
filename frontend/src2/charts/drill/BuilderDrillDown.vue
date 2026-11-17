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

// It is a separate component, not a flag, because adding a query needs the
// workbook, and the desk island renders charts without one. A View mounts
// `ViewDrillDown` and loads none of this.
const props = defineProps<{
	subject: DrillSubject
	clicked: ChartSegmentClick
}>()

const emit = defineEmits<{ close: [] }>()

// Two checks, one on each side. Only the authoring endpoint returns the cut
// pipeline, and only to a user who can write the chart. The client checks the
// workbook: a user who can only read it cannot add a query to it.
const workbook = inject(workbookKey, null)
function openable(answer: DrillLevelData) {
	return Boolean(answer.operations?.length) && Boolean(workbook) && !workbook?.doc.read_only
}

// The rows level on screen, if any. Its answer reflects the reader's latest
// filter, sort and find.
const $rows = ref<InstanceType<typeof DrillRowsView> | null>(null)

// The new query runs as its own author. It keeps the level's cut, but not the
// chart's Run as owner setting.
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
			// a dashboard filter on a query that the chart's query reads has no
			// operation in the new query, so it has more rows than the dialog showed
			if (answer.unapplied_filters?.length) {
				toast.warning(
					__(
						'The new query does not apply the dashboard filters: {0}',
						answer.unapplied_filters.join(', '),
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
