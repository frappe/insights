<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { Dropdown } from 'frappe-ui'
import {
	Copy,
	CopyPlus,
	ExternalLink,
	ImageDown,
	MoreHorizontal,
	RefreshCcw,
	Scroll,
	Share2,
	XIcon,
} from 'lucide-vue-next'
import { h, provide, ref } from 'vue'
import session from '../../session'
import { __ } from '../../translation'
import ViewSQLDialog from '../../query/components/ViewSQLDialog.vue'
import { duplicateWorkbookItem } from '../../workbook/workbook_items'
import type { ChartRead } from '../chart_read'

const props = defineProps<{
	chart: any
	preview: ChartRead
	chartEl: HTMLElement | null
	onDownload: () => void
	onShare: () => void
}>()

const showViewSQLDialog = ref(false)
// the SQL on show is the one the server sent back with the rows, so what is
// debugged here is what ran
provide('query', props.preview)

const moreActions = [
	{
		label: __('Export as PNG'),
		icon: h(ImageDown, { class: 'h-3 w-3 text-ink-gray-6', strokeWidth: 1.5 }),
		onClick: () => props.onDownload(),
		condition: () => !!props.chartEl,
	},
	{
		label: __('Share Chart'),
		icon: h(Share2, { class: 'h-3 w-3 text-ink-gray-6', strokeWidth: 1.5 }),
		onClick: () => props.onShare(),
		condition: () => !props.chart.doc.read_only,
	},
	{
		label: __('Duplicate Chart'),
		icon: h(CopyPlus, { class: 'h-3 w-3 text-ink-gray-6', strokeWidth: 1.5 }),
		onClick: () => duplicateWorkbookItem(props.chart, 'chart'),
	},
	{
		label: __('Reset Options'),
		icon: h(XIcon, { class: 'h-3 w-3 text-ink-gray-6', strokeWidth: 1.5 }),
		onClick: () => props.chart.resetConfig(),
		condition: () => !props.chart.doc.read_only,
	},
	{
		label: __('View SQL'),
		icon: h(Scroll, { class: 'h-3 w-3 text-ink-gray-6', strokeWidth: 1.5 }),
		onClick: () => (showViewSQLDialog.value = true),
	},
	{
		label: __('Copy JSON'),
		icon: h(Copy, { class: 'h-3 w-3 text-ink-gray-6', strokeWidth: 1.5 }),
		onClick: () => props.chart.copy(),
	},
	{
		label: __('Open in Desk'),
		icon: h(ExternalLink, { class: 'h-3 w-3 text-ink-gray-6', strokeWidth: 1.5 }),
		onClick: () => props.chart.openInDesk(),
		condition: () => session.user.has_desk_access,
	},
].filter((action) => !action.condition || action.condition() || !!action.condition)
</script>

<template>
	<div class="flex w-full flex-shrink-0 items-center justify-between bg-surface-base">
		<div>
			<div
				v-show="preview.result.executedSQL"
				class="tnum flex items-center gap-2 text-sm text-ink-gray-5"
			>
				<div class="h-2 w-2 rounded-full bg-green-500"></div>
				<div>
					<span v-if="preview.result.timeTaken == -1"> Fetched from cache </span>
					<span v-else> Fetched in {{ preview.result.timeTaken }}s </span>
					<span> {{ useTimeAgo(preview.result.lastExecutedAt).value }} </span>
				</div>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<Button variant="outline" label="Refresh" @click="() => preview.load(true)">
				<template #prefix>
					<RefreshCcw class="h-3 w-3 text-ink-gray-6" stroke-width="1.5" />
				</template>
			</Button>
			<Dropdown align="end" :options="moreActions">
				<Button variant="outline">
					<template #icon>
						<MoreHorizontal class="h-3 w-3 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
			</Dropdown>
		</div>
	</div>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
