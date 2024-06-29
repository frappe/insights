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
import { h, inject, ref, watch } from 'vue'
import { Operation } from '../../types/query.types'
import { Query } from '../query'
import ColumnsSelectorDialog from './ColumnsSelectorDialog.vue'
import FiltersSelectorDialog from './FiltersSelectorDialog.vue'
import JoinSelectorDialog from './JoinSelectorDialog.vue'
import NewColumnSelectorDialog from './NewColumnSelectorDialog.vue'
import SourceSelectorDialog from './SourceSelectorDialog.vue'
import ViewSQLDialog from './ViewSQLDialog.vue'

const query = inject('query') as Query

const showColumnsSelectorDialog = ref(false)
const showFiltersSelectorDialog = ref(false)
const showJoinSelectorDialog = ref(false)
const showNewColumnSelectorDialog = ref(false)
const showSourceSelectorDialog = ref(false)
const showViewSQLDialog = ref(false)

watch(
	() => query.activeEditOperation,
	(operation: Operation) => {
		switch (operation.type) {
			case 'source':
				showSourceSelectorDialog.value = true
				break
			case 'join':
				showJoinSelectorDialog.value = true
				break
			case 'select':
				showColumnsSelectorDialog.value = true
				break
			case 'filter':
				showFiltersSelectorDialog.value = true
				break
			case 'mutate':
				showNewColumnSelectorDialog.value = true
				break
			default:
				break
		}
	}
)

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
		onClick: () => (showFiltersSelectorDialog.value = true),
	},
	{
		label: 'Join Table',
		icon: h(BlendIcon, { class: '-rotate-45' }),
		onClick: () => (showJoinSelectorDialog.value = true),
	},
	// {
	// 	label: 'Sort Rows',
	// 	icon: ArrowUpDown,
	// },
	{
		label: 'Create Columns',
		icon: Sigma,
		onClick: () => (showNewColumnSelectorDialog.value = true),
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
		onClick: () => (showViewSQLDialog.value = true),
	},
	{
		label: 'Execute',
		icon: PlayIcon,
		onClick: () => query.execute(),
	},
]
</script>

<template>
	<div class="flex items-center gap-2">
		<Tooltip
			:key="idx"
			v-for="(action, idx) in actions"
			placement="top"
			:hover-delay="0.1"
			:text="action.label"
		>
			<Button :variant="'ghost'" @click="action.onClick" class="h-8 w-8 bg-white shadow">
				<template #icon>
					<component
						:is="action.icon"
						class="h-4.5 w-4.5 text-gray-700"
						stroke-width="1.5"
					/>
				</template>
			</Button>
		</Tooltip>
	</div>

	<SourceSelectorDialog
		v-if="showSourceSelectorDialog"
		v-model="showSourceSelectorDialog"
		@update:model-value="!$event && query.setActiveEditIndex(-1)"
		:source="
			query.activeEditOperation.type === 'source' ? query.activeEditOperation : undefined
		"
		@select="query.setSource($event)"
	/>

	<JoinSelectorDialog
		v-if="showJoinSelectorDialog"
		v-model="showJoinSelectorDialog"
		@select="query.addJoin($event)"
	/>

	<ColumnsSelectorDialog
		v-if="showColumnsSelectorDialog"
		v-model="showColumnsSelectorDialog"
		@select="query.selectColumns($event)"
	/>
	<FiltersSelectorDialog
		v-if="showFiltersSelectorDialog"
		v-model="showFiltersSelectorDialog"
		@update:model-value="!$event && query.setActiveEditIndex(-1)"
		:filter="
			query.activeEditOperation.type === 'filter' ? query.activeEditOperation : undefined
		"
		:filter-group="
			query.activeEditOperation.type === 'filter_group'
				? query.activeEditOperation
				: undefined
		"
		:column-options="query.result.columnOptions"
		@select="query.addFilterGroup($event)"
	/>
	<NewColumnSelectorDialog
		v-if="showNewColumnSelectorDialog"
		v-model="showNewColumnSelectorDialog"
		@select="query.addMutate($event)"
	/>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
