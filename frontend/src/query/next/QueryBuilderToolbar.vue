<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import {
	ArrowUpDown,
	BlendIcon,
	ColumnsIcon,
	Combine,
	Database,
	FilterIcon,
	GitBranch,
	GitMerge,
	PlayIcon,
	Sigma,
} from 'lucide-vue-next'
import { h, inject, ref } from 'vue'
import SourceSelectorDialog from './SourceSelectorDialog.vue'
import ColumnsSelectorDialog from './ColumnsSelectorDialog.vue'
import { QueryPipeline } from './useQueryPipeline'

const queryPipeline = inject('queryPipeline') as QueryPipeline
const showSourceSelectorDialog = ref(false)
const showColumnsSelectorDialog = ref(false)
const actions = [
	{
		label: 'Change Source',
		icon: Database,
		onClick: () => (showSourceSelectorDialog.value = true),
	},
	{
		label: 'Select Columns',
		icon: ColumnsIcon,
		onClick: () => (showColumnsSelectorDialog.value = true),
	},
	{
		label: 'Filter Rows',
		icon: FilterIcon,
	},
	{
		label: 'Join Table',
		icon: h(BlendIcon, { class: '-rotate-45' }),
	},
	{
		label: 'Sort Rows',
		icon: ArrowUpDown,
	},
	{
		label: 'Create Columns',
		icon: Sigma,
	},
	{
		label: 'Summarize',
		icon: Combine,
	},
	{
		label: 'Pivot',
		icon: GitBranch,
	},
	{
		label: 'Unpivot',
		icon: GitMerge,
	},
]
</script>

<template>
	<div class="flex items-center divide-x border-b">
		<Tooltip
			:key="idx"
			v-for="(action, idx) in actions"
			placement="top"
			:hover-delay="0.1"
			:text="action.label"
		>
			<!-- <component v-if="action.component" :is="action.component" /> -->
			<!-- v-else -->
			<Button :variant="'ghost'" @click="action.onClick" size="lg" class="rounded-none">
				<template #icon>
					<component :is="action.icon" class="h-5 w-5 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
		</Tooltip>
		<Tooltip placement="bottom" :hover-delay="0.1" :text="'Execute'" class="border-r">
			<Button
				size="lg"
				variant="ghost"
				class="rounded-none"
				:disabled="queryPipeline.steps.length === 0"
				:loading="queryPipeline.executing"
				@click="queryPipeline.execute"
			>
				<template #icon>
					<PlayIcon class="h-5 w-5 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
		</Tooltip>
	</div>

	<SourceSelectorDialog
		v-model="showSourceSelectorDialog"
		@select="queryPipeline.setSource($event)"
	/>
	<ColumnsSelectorDialog
		v-model="showColumnsSelectorDialog"
		@select="queryPipeline.selectColumns($event)"
	/>
</template>
