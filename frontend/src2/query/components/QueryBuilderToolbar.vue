<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { CodeIcon, Download, PlayIcon } from 'lucide-vue-next'
import { inject, ref, watch } from 'vue'
import { Operation } from '../../types/query.types'
import { query_operation_types } from '../helpers'
import { Query } from '../query'
import ColumnsSelectorDialog from './ColumnsSelectorDialog.vue'
import CustomScriptDialog from './CustomScriptDialog.vue'
import FiltersSelectorDialog from './FiltersSelectorDialog.vue'
import JoinSelectorDialog from './JoinSelectorDialog.vue'
import NewColumnSelectorDialog from './NewColumnSelectorDialog.vue'
import SourceSelectorDialog from './source_selector/SourceSelectorDialog.vue'
import SummarySelectorDialog from './SummarySelectorDialog.vue'
import UnionSelectorDialog from './UnionSelectorDialog.vue'
import ViewSQLDialog from './ViewSQLDialog.vue'

const query = inject('query') as Query

const showSourceSelectorDialog = ref(false)
const showJoinSelectorDialog = ref(false)
const showUnionSelectorDialog = ref(false)
const showColumnsSelectorDialog = ref(false)
const showFiltersSelectorDialog = ref(false)
const showNewColumnSelectorDialog = ref(false)
const showSummarySelectorDialog = ref(false)
const showCustomScriptDialog = ref(false)
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
			case 'union':
				showUnionSelectorDialog.value = true
				break
			case 'select':
				showColumnsSelectorDialog.value = true
				break
			case 'filter':
			case 'filter_group':
				showFiltersSelectorDialog.value = true
				break
			case 'mutate':
				showNewColumnSelectorDialog.value = true
				break
			case 'summarize':
				showSummarySelectorDialog.value = true
				break
			case 'custom_operation':
				showCustomScriptDialog.value = true
				break
			default:
				break
		}
	}
)

const actions = [
	{
		label: 'Change Source',
		icon: query_operation_types.source.icon,
		onClick: () => (showSourceSelectorDialog.value = true),
	},
	{
		label: 'Select Columns',
		icon: query_operation_types.select.icon,
		onClick: () => (showColumnsSelectorDialog.value = true),
	},
	{
		label: 'Filter Rows',
		icon: query_operation_types.filter.icon,
		onClick: () => (showFiltersSelectorDialog.value = true),
	},
	{
		label: 'Join Table',
		icon: query_operation_types.join.icon,
		onClick: () => (showJoinSelectorDialog.value = true),
	},
	{
		label: 'Append Table',
		icon: query_operation_types.union.icon,
		onClick: () => (showUnionSelectorDialog.value = true),
	},
	// {
	// 	label: 'Sort Rows',
	// 	icon: ArrowUpDown,
	// },
	{
		label: 'Create Columns',
		icon: query_operation_types.mutate.icon,
		onClick: () => (showNewColumnSelectorDialog.value = true),
	},
	{
		label: 'Summarize',
		icon: query_operation_types.summarize.icon,
		onClick: () => (showSummarySelectorDialog.value = true),
	},
	{
		label: 'Custom Script',
		icon: query_operation_types.custom_operation.icon,
		onClick: () => (showCustomScriptDialog.value = true),
	},
	// {
	// 	label: 'Pivot',
	// 	icon: GitBranch,
	// },
	// {
	// 	label: 'Unpivot',
	// 	icon: GitMerge,
	// },
	{
		type: 'separator',
	},
	{
		label: 'Download Data',
		icon: Download,
		onClick: () => query.downloadResults(),
	},
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
	<div class="flex w-full flex-shrink-0 justify-between bg-gray-50 p-2">
		<div class="flex w-full items-center gap-2">
			<template v-for="(action, idx) in actions" :key="idx">
				<div v-if="action.type === 'separator'" class="h-8 flex-1"></div>
				<Tooltip v-else placement="top" :hover-delay="0.1" :text="action.label">
					<Button
						:variant="'ghost'"
						@click="action.onClick"
						class="h-8 w-8 bg-white shadow"
					>
						<template #icon>
							<component
								:is="action.icon"
								class="h-4.5 w-4.5 text-gray-700"
								stroke-width="1.5"
							/>
						</template>
					</Button>
				</Tooltip>
			</template>
		</div>
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
		@update:model-value="!$event && query.setActiveEditIndex(-1)"
		:join="query.activeEditOperation.type === 'join' ? query.activeEditOperation : undefined"
		@select="query.addJoin($event)"
	/>

	<UnionSelectorDialog
		v-if="showUnionSelectorDialog"
		v-model="showUnionSelectorDialog"
		@update:model-value="!$event && query.setActiveEditIndex(-1)"
		:union="query.activeEditOperation.type === 'union' ? query.activeEditOperation : undefined"
		@select="query.addUnion($event)"
	/>

	<ColumnsSelectorDialog
		v-if="showColumnsSelectorDialog"
		v-model="showColumnsSelectorDialog"
		@update:model-value="!$event && query.setActiveEditIndex(-1)"
		:columns="
			query.activeEditOperation.type === 'select' ? query.activeEditOperation : undefined
		"
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
		@update:model-value="!$event && query.setActiveEditIndex(-1)"
		:mutation="
			query.activeEditOperation.type === 'mutate' ? query.activeEditOperation : undefined
		"
		:column-options="query.result.columnOptions"
		@select="query.addMutate($event)"
	/>

	<SummarySelectorDialog
		v-if="showSummarySelectorDialog"
		v-model="showSummarySelectorDialog"
		@update:model-value="!$event && query.setActiveEditIndex(-1)"
		:summary="
			query.activeEditOperation.type === 'summarize' ? query.activeEditOperation : undefined
		"
		@select="query.addSummarize($event)"
	/>

	<CustomScriptDialog
		v-if="showCustomScriptDialog"
		v-model="showCustomScriptDialog"
		@update:model-value="!$event && query.setActiveEditIndex(-1)"
		:operation="
			query.activeEditOperation.type === 'custom_operation'
				? query.activeEditOperation
				: undefined
		"
		:column-options="query.result.columnOptions"
		@select="query.addCustomOperation($event)"
	/>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
</template>
