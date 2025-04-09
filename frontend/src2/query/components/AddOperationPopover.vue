<script setup lang="tsx">
import { Plus } from 'lucide-vue-next'
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

const query = inject('query') as Query

const showSourceSelectorDialog = ref(false)
const showJoinSelectorDialog = ref(false)
const showUnionSelectorDialog = ref(false)
const showColumnsSelectorDialog = ref(false)
const showFiltersSelectorDialog = ref(false)
const showNewColumnSelectorDialog = ref(false)
const showSummarySelectorDialog = ref(false)
const showCustomScriptDialog = ref(false)

const operationButtons = [
	{
		label: 'Select Source',
		description: 'Select a table or query to start building your query',
		icon: query_operation_types.source.icon,
		onClick: () => (showSourceSelectorDialog.value = true),
	},
	{
		label: 'Choose Columns',
		description: 'Show or hide columns from the table',
		icon: query_operation_types.select.icon,
		onClick: () => (showColumnsSelectorDialog.value = true),
	},
	{
		label: 'Filter Rows',
		description: 'Filter rows based on columns or expressions',
		icon: query_operation_types.filter.icon,
		onClick: () => (showFiltersSelectorDialog.value = true),
	},
	{
		label: 'Join Table',
		description: 'Join this table with another table or query',
		icon: query_operation_types.join.icon,
		onClick: () => (showJoinSelectorDialog.value = true),
	},
	{
		label: 'Append Table',
		description: 'Append this table with another table or query',
		icon: query_operation_types.union.icon,
		onClick: () => (showUnionSelectorDialog.value = true),
	},
	{
		label: 'Add New Column',
		description: 'Add a new column based on existing columns',
		icon: query_operation_types.mutate.icon,
		onClick: () => (showNewColumnSelectorDialog.value = true),
	},
	{
		label: 'Group & Summarize',
		description: 'Group rows by columns and summarize the data',
		icon: query_operation_types.summarize.icon,
		onClick: () => (showSummarySelectorDialog.value = true),
	},
	{
		label: 'Custom Operation',
		description: 'Apply a custom operation using python script',
		icon: query_operation_types.custom_operation.icon,
		onClick: () => (showCustomScriptDialog.value = true),
	},
]

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
</script>

<template>
	<Popover placement="left-start" popover-class="!min-w-fit pr-5">
		<template #target="{ togglePopover, isOpen }">
			<div class="group relative flex cursor-pointer items-center gap-2">
				<Button
					variant="outline"
					label="Add Operation"
					class="-ml-[14px] !h-6 !gap-1.5 bg-white !px-2 text-p-xs"
					@click="togglePopover"
				>
					<template #prefix>
						<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</div>
		</template>
		<template #body-main="{ togglePopover, isOpen }">
			<div v-if="isOpen" class="flex flex-col p-1.5">
				<span class="flex h-6 items-center px-2 text-p-xs text-gray-500">
					Select an operation
				</span>
				<div class="grid grid-cols-2">
					<Button
						v-for="button in operationButtons"
						:key="button.label"
						variant="ghost"
						class="!h-fit w-full !justify-start"
						@click="
							() => {
								button.onClick()
								togglePopover()
							}
						"
					>
						<template #prefix>
							<div class="flex items-start gap-2 py-2">
								<component
									:is="button.icon"
									class="h-4.5 w-4.5 flex-shrink-0 text-gray-700"
									stroke-width="1.5"
								/>
								<div class="flex flex-1 flex-col text-left">
									<p class="truncate text-p-sm">{{ button.label }}</p>
									<p class="w-40 text-p-xs text-gray-500">
										{{ button.description }}
									</p>
								</div>
							</div>
						</template>
					</Button>
				</div>
			</div>
		</template>
	</Popover>

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
</template>
