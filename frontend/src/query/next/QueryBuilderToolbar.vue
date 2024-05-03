<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import {
	BlendIcon,
	CodeIcon,
	ColumnsIcon,
	Database,
	FilterIcon,
	PlayIcon,
	Sigma,
} from 'lucide-vue-next'
import { h, inject } from 'vue'

import ColumnsSelectorDialog from './ColumnsSelectorDialog.vue'
import FiltersSelectorDialog from './FiltersSelectorDialog.vue'
import JoinSelectorDialog from './JoinSelectorDialog.vue'
import NewColumnSelectorDialog from './NewColumnSelectorDialog.vue'
import SourceSelectorDialog from './SourceSelectorDialog.vue'
import ViewSQLDialog from './ViewSQLDialog.vue'
import { Query } from './useQuery'

const emit = defineEmits(['change-source'])
const query = inject('query') as Query

const actions = [
	{
		label: 'Change Source',
		icon: Database,
		onClick: () => (query.showSourceSelectorDialog = true),
	},
	{
		label: 'Select Columns',
		icon: ColumnsIcon,
		onClick: () => (query.showColumnsSelectorDialog = true),
	},
	{
		label: 'Filter Rows',
		icon: FilterIcon,
		onClick: () => (query.showFiltersSelectorDialog = true),
	},
	{
		label: 'Join Table',
		icon: h(BlendIcon, { class: '-rotate-45' }),
		onClick: () => (query.showJoinSelectorDialog = true),
	},
	// {
	// 	label: 'Sort Rows',
	// 	icon: ArrowUpDown,
	// },
	{
		label: 'Create Columns',
		icon: Sigma,
		onClick: () => (query.showNewColumnSelectorDialog = true),
	},
	// {
	// 	label: 'Summarize',
	// 	icon: Combine,
	// },
	// {
	// 	label: 'Pivot',
	// 	icon: GitBranch,
	// },
	// {
	// 	label: 'Unpivot',
	// 	icon: GitMerge,
	// },
	{
		label: 'View SQL',
		icon: CodeIcon,
		onClick: () => (query.showViewSQLDialog = true),
	},
	{
		label: 'Execute',
		icon: PlayIcon,
		onClick: () => query.execute(),
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
			<Button :variant="'ghost'" @click="action.onClick" size="lg" class="rounded-none">
				<template #icon>
					<component :is="action.icon" class="h-5 w-5 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
		</Tooltip>
	</div>

	<SourceSelectorDialog
		v-if="query.showSourceSelectorDialog"
		v-model="query.showSourceSelectorDialog"
		@select="query.setSource($event)"
	/>

	<JoinSelectorDialog
		v-if="query.showJoinSelectorDialog"
		v-model="query.showJoinSelectorDialog"
		@select="query.addJoin($event)"
	/>

	<ColumnsSelectorDialog
		v-if="query.showColumnsSelectorDialog"
		v-model="query.showColumnsSelectorDialog"
		@select="query.selectColumns($event)"
	/>
	<FiltersSelectorDialog
		v-if="query.showFiltersSelectorDialog"
		v-model="query.showFiltersSelectorDialog"
		@select="query.addFilter($event)"
	/>
	<NewColumnSelectorDialog
		v-if="query.showNewColumnSelectorDialog"
		v-model="query.showNewColumnSelectorDialog"
		@select="query.addMutate($event)"
	/>

	<ViewSQLDialog v-if="query.showViewSQLDialog" v-model="query.showViewSQLDialog" />
</template>
