<script setup lang="tsx">
import { MoreHorizontal } from 'lucide-vue-next'
import { inject } from 'vue'
import {
	ColumnDataType,
	FilterOperator,
	FilterValue,
	QueryResultColumn,
	SortDirection,
} from '../../types/query.types'
import { column as _column } from '../helpers'
import { Query } from '../query'
import ColumnFilter from './ColumnFilter.vue'
import ColumnRemove from './ColumnRemove.vue'
import ColumnSort from './ColumnSort.vue'
import ColumnTypeChange from './ColumnTypeChange.vue'
import QueryDataTable from './QueryDataTable.vue'

const query = inject('query') as Query

function onTypeChange(column: QueryResultColumn, new_type: ColumnDataType) {
	if (new_type === column.type) return
	query.changeColumnType(column.name, new_type)
}

function onRemove(column: QueryResultColumn) {
	query.removeColumn(column.name)
}

function onSort(column: QueryResultColumn, sort_order: SortDirection) {
	if (!sort_order) {
		query.removeOrderBy(column.name)
		return
	}
	query.addOrderBy({
		column: _column(column.name),
		direction: sort_order,
	})
}

function onFilter(
	column: QueryResultColumn,
	filter_operator: FilterOperator,
	filter_value: FilterValue
) {
	query.addFilterGroup({
		logical_operator: 'And',
		filters: [
			{
				column: _column(column.name),
				operator: filter_operator,
				value: filter_value,
			},
		],
	})
}
</script>

<template>
	<div class="relative flex w-full flex-1 flex-col overflow-hidden rounded shadow">
		<QueryDataTable :query="query" :enable-column-rename="true" :enable-alerts="true">
			<template #header-prefix="{ column }">
				<ColumnTypeChange :column="column" @typeChange="onTypeChange(column, $event)" />
			</template>

			<template #header-suffix="{ column }">
				<div class="ml-auto pl-2">
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
								<ColumnSort
									:column="column"
									@sort="onSort(column, $event), togglePopover()"
								/>
								<ColumnFilter
									:column="column"
									@filter="
										(op, val) => (onFilter(column, op, val), togglePopover())
									"
									:valuesProvider="(searchTxt: string) => query.getDistinctColumnValues(column.name, searchTxt)"
								/>
								<ColumnRemove
									:column="column"
									@remove="onRemove(column), togglePopover()"
								/>
							</div>
						</template>
					</Popover>
				</div>
			</template>
		</QueryDataTable>
	</div>
</template>
