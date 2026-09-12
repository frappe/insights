<script setup lang="ts">
import { Button, Dropdown } from 'frappe-ui'
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
import { computed, h, provide, ref, type VNode } from 'vue'
import ViewSQLDialog from '../../query/components/ViewSQLDialog.vue'
import session from '../../session'
import { __ } from '../../translation'
import { duplicateWorkbookItem } from '../../workbook/workbook_items'
import type { ChartRead } from '../chart_read'

// What the builder puts in the chart card's own header. The card heads the page,
// so these are the page's acts: run it again, and everything else in a menu.
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

type MoreAction = {
	label: string
	icon: VNode
	onClick: () => void
	condition?: () => boolean
}

const moreActions = computed(() =>
	(
		[
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
		] as MoreAction[]
	)
		.filter((action) => !action.condition || action.condition())
		.map(({ label, icon, onClick }) => ({ label, icon, onClick })),
)
</script>

<template>
	<!-- read out of the PNG the menu exports: the acts are chrome, not the chart -->
	<div class="flex items-center gap-1" data-export-exclude>
		<Button variant="ghost" :tooltip="__('Refresh')" @click="preview.load(true)">
			<template #icon>
				<RefreshCcw class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
			</template>
		</Button>
		<Dropdown align="end" :options="moreActions">
			<Button variant="ghost" :tooltip="__('More')">
				<template #icon>
					<MoreHorizontal class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
				</template>
			</Button>
		</Dropdown>
	</div>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
