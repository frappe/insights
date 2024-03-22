<script setup lang="ts">
import { inject } from 'vue'
import ColumnFilter from './components/ColumnFilter.vue'
import ColumnRemove from './components/ColumnRemove.vue'
import ColumnRename from './components/ColumnRename.vue'
import ColumnSort from './components/ColumnSort.vue'
import ColumnTypeChange from './components/ColumnTypeChange.vue'
import { column } from './pipeline_utils'
import { QueryPipeline, QueryPipelineResultColumn } from './useQueryPipeline'

const props = defineProps<{ column: QueryPipelineResultColumn }>()

const queryPipeline = inject('queryPipeline') as QueryPipeline

function onRename(new_name: string, togglePopover: () => void) {
	queryPipeline.renameColumn(props.column.name, new_name)
	togglePopover()
}

function onTypeChange(new_type: string, togglePopover: () => void) {
	queryPipeline.changeColumnType(props.column.name, new_type)
	togglePopover()
}

function onRemove(togglePopover: () => void) {
	queryPipeline.removeColumn(props.column.name)
	togglePopover()
}

function onSort(sort_order: 'asc' | 'desc' | '', togglePopover: () => void) {
	if (!sort_order) {
		queryPipeline.removeOrderBy(props.column.name)
		togglePopover()
		return
	}
	queryPipeline.addOrderBy({
		column: column(props.column.name),
		direction: sort_order,
	})
	togglePopover()
}

function onFilter(
	filter_operator: FilterOperator,
	filter_value: FilterValue,
	togglePopover: () => void
) {
	queryPipeline.addFilter({
		column: column(props.column.name),
		operator: filter_operator,
		value: filter_value,
	})
	togglePopover()
}
</script>

<template>
	<Popover placement="bottom">
		<template #target="{ togglePopover, isOpen }">
			<Button
				variant="ghost"
				class="flex !h-12 w-full !justify-start rounded-none border border-transparent px-3 text-left"
				:class="{
					'!border-gray-600 !bg-gray-100': isOpen,
				}"
				@click="togglePopover"
			>
				<div class="flex flex-col gap-1 truncate">
					<span>{{ props.column.name }}</span>
					<span class="text-sm text-gray-600">
						{{ props.column.type }}
					</span>
				</div>
			</Button>
		</template>
		<template #body-main="{ togglePopover, isOpen }">
			<div v-if="isOpen" class="flex min-w-[10rem] flex-col p-1.5">
				<!-- Rename, Sort, Filter, Summarize, Describe, Pivot, Remove -->
				<ColumnRename :column="props.column" @rename="onRename($event, togglePopover)" />
				<ColumnTypeChange
					:column="props.column"
					@typeChange="onTypeChange($event, togglePopover)"
				/>
				<ColumnSort :column="props.column" @sort="onSort($event, togglePopover)" />
				<ColumnFilter
					:column="props.column"
					@filter="(op, val) => onFilter(op, val, togglePopover)"
				/>
				<ColumnRemove :column="props.column" @remove="onRemove(togglePopover)" />
			</div>
		</template>
	</Popover>
</template>
