<script setup lang="tsx">
import { toast } from 'frappe-ui'
import { Check, MoreHorizontal, X } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import {
	ColumnDataType,
	FilterOperator,
	FilterValue,
	MutateArgs,
	QueryResultColumn,
	SortDirection,
} from '../../types/query.types'
import { column as _column, expression } from '../helpers'
import { Query } from '../query'
import ColumnFilter from './ColumnFilter.vue'
import ColumnRemove from './ColumnRemove.vue'
import ColumnSort from './ColumnSort.vue'
import ColumnTypeChange from './ColumnTypeChange.vue'
import ResultPane from '../../components/result_pane/ResultPane.vue'
import QueryDataTable from './QueryDataTable.vue'
import AuthoringDrillDown from '../../charts/drill/AuthoringDrillDown.vue'
import type { ChartSegmentClick } from '../../charts/drill/segment_click'
import type { DrillSubject } from '../../charts/drill/drill_stack'
import { queryDrillSubject } from '../../charts/drill/query_drill'
import ExpressionEditor from './ExpressionEditor.vue'
import { copy } from '../../helpers'
import { __ } from '../../translation'

const props = defineProps<{ findTarget?: HTMLElement | null }>()
const query = inject('query') as Query

// A summarized cell opens the same dialog a chart segment does. The candidates
// are the one thing this surface has to ask for, so the click waits on them
// rather than drawing a menu that would fill in under the reader's cursor.
const drill = ref<{ subject: DrillSubject; clicked: ChartSegmentClick }>()
async function onSegmentClick(clicked: ChartSegmentClick) {
	const subject = await queryDrillSubject(query)
	if (!subject) {
		toast.warning(__('Nothing to drill into'), {
			description: __('Only a summarized result has rows behind its numbers'),
		})
		return
	}
	drill.value = { subject, clicked }
}

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
	filter_value: FilterValue,
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

const emptyColumn = {
	expression: expression(''),
	data_type: 'Auto' as ColumnDataType,
	new_name: 'new_column',
}

const newColumn = ref<MutateArgs>(copy(emptyColumn))

function addNewColumn() {
	query.addMutate(newColumn.value)
	newColumn.value = copy(emptyColumn)
}
</script>

<template>
	<ResultPane :query="query" :find-target="props.findTarget">
		<template #grid="{ rows, currentPage, pageSize }">
			<QueryDataTable
				:query="query"
				:rows="rows"
				:current-page="currentPage"
				:page-size="pageSize"
				:enable-column-rename="true"
				:enable-new-column="true"
				:enable-drill-down="true"
				@segment-click="onSegmentClick"
			>
				<template #header-prefix="{ column }">
					<ColumnTypeChange
						:model-value="column.type"
						@update:model-value="onTypeChange(column, $event)"
					/>
				</template>

				<template #header-suffix="{ column }">
					<div class="ml-auto pl-2">
						<Popover side="bottom" align="end">
							<template #trigger="{ open }">
								<Button
									variant="ghost"
									class="rounded-1"
									:class="open ? '!bg-surface-gray-2' : ''"
								>
									<template #icon>
										<MoreHorizontal class="h-4 w-4 text-ink-gray-6" />
									</template>
								</Button>
							</template>
							<template #default="{ toggle: togglePopover, open }">
								<div v-if="open" class="flex min-w-[10rem] flex-col p-1">
									<ColumnSort
										:column="column"
										@sort="onSort(column, $event), togglePopover()"
									/>
									<ColumnFilter
										:column="column"
										@filter="
											(op, val) => (
												onFilter(column, op, val), togglePopover()
											)
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

				<template #new-column-editor="{ toggle }">
					<div class="flex h-full min-w-64 w-auto items-center gap-1 pl-0.5">
						<ColumnTypeChange v-model="newColumn.data_type" />
						<ExpressionEditor
							class="inline-expression h-fit max-h-[10rem] text-sm flex-1"
							v-model="newColumn.expression.expression"
							:column-options="query.result.columnOptions"
							language="python"
							:placeholder="''"
							:hide-line-numbers="true"
							:multi-line="false"
						/>
						<Button
							variant="ghost"
							class="flex-shrink-0"
							@click="addNewColumn(), toggle()"
						>
							<template #icon>
								<Check class="size-4 text-ink-gray-6" :stroke-width="1.5" />
							</template>
						</Button>
						<Button variant="ghost" class="flex-shrink-0" @click="toggle">
							<template #icon>
								<X class="size-4 text-ink-gray-6" :stroke-width="1.5" />
							</template>
						</Button>
					</div>
				</template>
			</QueryDataTable>
		</template>
	</ResultPane>

	<!-- keyed on the click, so every drill starts from an empty stack -->
	<AuthoringDrillDown
		v-if="drill"
		:subject="drill.subject"
		:clicked="drill.clicked"
		:adhoc-filters="query.adhocFilters"
		@close="drill = undefined"
	/>
</template>
