<script setup lang="ts">
import ContentEditable from '@/components/ContentEditable.vue'
import { MoreHorizontal } from 'lucide-vue-next'
import { inject } from 'vue'
import ColumnFilter from './components/ColumnFilter.vue'
import ColumnRemove from './components/ColumnRemove.vue'
import ColumnSort from './components/ColumnSort.vue'
import ColumnTypeChange from './components/ColumnTypeChange.vue'
import { column } from './pipeline_utils'
import { QueryPipeline, QueryPipelineResultColumn } from './useQueryPipeline'

const props = defineProps<{ column: QueryPipelineResultColumn }>()

const queryPipeline = inject('queryPipeline') as QueryPipeline

function onRename(new_name: string) {
	if (new_name === props.column.name) return
	queryPipeline.renameColumn(props.column.name, new_name)
}

function onTypeChange(new_type: ColumnType) {
	if (new_type === props.column.type) return
	queryPipeline.changeColumnType(props.column.name, new_type)
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
	<div class="flex w-full items-center justify-between gap-8">
		<div class="flex items-center">
			<ColumnTypeChange :column="props.column" @typeChange="onTypeChange" />
			<ContentEditable
				:modelValue="props.column.name"
				placeholder="Column Name"
				class="flex h-6 items-center rounded-sm px-0.5 text-base focus:ring-1 focus:ring-gray-700 focus:ring-offset-1"
				@returned="onRename"
				@blur="onRename"
			/>
		</div>
		<Popover placement="bottom-end">
			<template #target="{ togglePopover, isOpen }">
				<Button
					variant="ghost"
					class="rounded-sm"
					@click="togglePopover"
					:class="isOpen ? '!bg-gray-100' : ''"
				>
					<template #icon>
						<MoreHorizontal class="h-4 w-4 text-gray-700" />
					</template>
				</Button>
			</template>
			<template #body-main="{ togglePopover, isOpen }">
				<div v-if="isOpen" class="flex min-w-[10rem] flex-col p-1">
					<!-- Rename, Sort, Filter, Summarize, Describe, Pivot, Remove -->
					<ColumnSort :column="props.column" @sort="onSort($event, togglePopover)" />
					<ColumnFilter
						:column="props.column"
						@filter="(op, val) => onFilter(op, val, togglePopover)"
					/>
					<ColumnRemove :column="props.column" @remove="onRemove(togglePopover)" />
				</div>
			</template>
		</Popover>
	</div>
</template>
