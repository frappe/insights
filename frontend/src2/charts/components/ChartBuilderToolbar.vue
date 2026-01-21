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
	Share2,
	XIcon,
} from 'lucide-vue-next'
import { h } from 'vue'
import session from '../../session'

const props = defineProps<{
	chart: any
	chartEl: HTMLElement | null
	onDownload: () => void
	onShare: () => void
}>()

const moreActions = [
	{
		label: 'Export as PNG',
		icon: h(ImageDown, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.onDownload(),
		condition: () => !!props.chartEl,
	},
	{
		label: 'Share Chart',
		icon: h(Share2, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.onShare(),
		condition: () => !props.chart.doc.read_only,
	},
	{
		label: 'Duplicate Chart',
		icon: h(CopyPlus, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.chart.duplicate(),
	},
	{
		label: 'Reset Options',
		icon: h(XIcon, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.chart.resetConfig(),
		condition: () => !props.chart.doc.read_only,
	},
	{
		label: 'Copy JSON',
		icon: h(Copy, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.chart.copy(),
	},
	{
		label: 'Open in Desk',
		icon: h(ExternalLink, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => props.chart.openInDesk(),
		condition: () => session.user.has_desk_access,
	},
].filter((action) => !action.condition || action.condition() || !!action.condition)
</script>

<template>
	<div class="flex w-full flex-shrink-0 items-center justify-between bg-white">
		<div>
			<div
				v-show="chart.dataQuery.result.executedSQL"
				class="tnum flex items-center gap-2 text-sm text-gray-600"
			>
				<div class="h-2 w-2 rounded-full bg-green-500"></div>
				<div>
					<span v-if="chart.dataQuery.result.timeTaken == -1"> Fetched from cache </span>
					<span v-else> Fetched in {{ chart.dataQuery.result.timeTaken }}s </span>
					<span> {{ useTimeAgo(chart.dataQuery.result.lastExecutedAt).value }} </span>
				</div>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<Button
				variant="ghost"
				label="Refresh"
				@click="() => chart.refresh(true)"
				class="!h-6 !gap-1.5 bg-white !px-2 text-xs shadow"
			>
				<template #prefix>
					<RefreshCcw class="h-3 w-3 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
			<Dropdown placement="right" :options="moreActions">
				<Button variant="ghost" class="!h-6 !gap-1.5 bg-white !px-2 text-xs shadow">
					<template #icon>
						<MoreHorizontal class="h-3 w-3 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Dropdown>
		</div>
	</div>
</template>
