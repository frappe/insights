<script setup lang="ts">
import { Button } from 'frappe-ui'
import { SlidersHorizontal, SquareArrowOutUpRight } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { __ } from '../../translation'
import type { AdhocFilters } from '../../types/query.types'
import { workbookKey } from '../../workbook/workbook_key'
import ChartDrillDown from './ChartDrillDown.vue'
import type { DrillLevelData, DrillSubject } from './drill_stack'
import DrillRows from './DrillRows.vue'
import type { ChartSegmentClick } from './segment_click'

// The same drill, plus the two things an author gets: the rows level as a query
// they can edit, and that query added to the workbook.
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
// a workbook this user only reads is not one to add a query to.
const workbook = inject(workbookKey, null)
function openable(answer: DrillLevelData) {
	return Boolean(answer.operations?.length) && Boolean(workbook) && !workbook?.doc.read_only
}

// The rows level's query, for as long as that level is on screen. It is mounted
// and dropped with the level, so the editor toggle and the reader's edits go
// with it too.
const $rows = ref<InstanceType<typeof DrillRows> | null>(null)

// What the author would be adding: the reader's own pipeline where they have
// been editing one, and the server's slice everywhere else.
function pipelineOf(answer: DrillLevelData) {
	return $rows.value?.query.doc.operations || answer.operations || []
}

function addToWorkbook(answer: DrillLevelData) {
	const title = `${props.subject.title} — ${__('Drill Down')}`
	const operations = pipelineOf(answer)
	confirmDialog({
		title: __('Open as Query'),
		message: __('“{0}” will be added to this workbook as a new query.', title),
		primaryActionLabel: __('Add Query'),
		onSuccess: () => {
			workbook?.addQuery({
				title,
				operations,
				use_live_connection: answer.use_live_connection,
			})
			emit('close')
		},
	})
}
</script>

<template>
	<ChartDrillDown :subject="props.subject" :clicked="props.clicked" @close="emit('close')">
		<template #actions="{ answer }">
			<!-- taking the level away as a query is offered wherever the reader
			     stands, so it sits with the way out rather than with the level -->
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

		<template #level-actions="{ answer }">
			<!-- the pipeline is there to be read on any level, but only a rows level
			     draws it: that is where the query the author is editing lives, and
			     only for a reader who could take it away as one -->
			<Button
				v-if="$rows && openable(answer)"
				variant="outline"
				:tooltip="__('Edit query')"
				:class="$rows.editing ? '!bg-surface-gray-3' : ''"
				@click="$rows.toggleEditor()"
			>
				<template #icon>
					<SlidersHorizontal class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
				</template>
			</Button>
		</template>

		<template #rows="{ answer, findTarget }">
			<DrillRows
				ref="$rows"
				:answer="answer"
				:title="props.subject.title"
				:adhoc-filters="props.adhocFilters"
				:find-target="findTarget"
			/>
		</template>
	</ChartDrillDown>
</template>
