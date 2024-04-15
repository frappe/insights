<script setup lang="ts">
import ContentEditable from '@/components/ContentEditable.vue'
import { MoreHorizontal } from 'lucide-vue-next'
import { inject } from 'vue'
import ColumnFilter from './components/ColumnFilter.vue'
import ColumnRemove from './components/ColumnRemove.vue'
import ColumnSort from './components/ColumnSort.vue'
import ColumnTypeChange from './components/ColumnTypeChange.vue'
import { column } from './query_utils'
import { Query, QueryResultColumn } from './useQuery'

const props = defineProps<{ column: QueryResultColumn }>()

const query = inject('query') as Query

function onRename(new_name: string) {
	if (new_name === props.column.name) return
	query.renameColumn(props.column.name, new_name)
}

function onTypeChange(new_type: ColumnDataType) {
	if (new_type === props.column.type) return
	query.changeColumnType(props.column.name, new_type)
}

function onRemove(togglePopover: () => void) {
	query.removeColumn(props.column.name)
	togglePopover()
}

function onSort(sort_order: 'asc' | 'desc' | '', togglePopover: () => void) {
	if (!sort_order) {
		query.removeOrderBy(props.column.name)
		togglePopover()
		return
	}
	query.addOrderBy({
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
	query.addFilter({
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
				class="flex h-6 items-center whitespace-nowrap rounded-sm px-0.5 text-base focus:ring-1 focus:ring-gray-700 focus:ring-offset-1"
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
