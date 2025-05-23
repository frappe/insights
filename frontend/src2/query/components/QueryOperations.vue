<script setup lang="tsx">
import { XIcon } from 'lucide-vue-next'
import { computed, inject } from 'vue'
import {
	Cast,
	CustomOperation,
	FilterGroup,
	Join,
	Limit,
	Mutate,
	OrderBy,
	Remove,
	Rename,
	Select,
	Source,
	Summarize,
	Union,
} from '../../types/query.types'
import { workbookKey } from '../../workbook/workbook'
import { query_operation_types } from '../helpers'
import { Query } from '../query'
import AddOperationPopover from './AddOperationPopover.vue'
import useQuery from '../query.ts'

const query = inject('query') as Query
const operations = computed(() => {
	return query.doc.operations.map((op) => {
		return {
			...op,
			meta: query_operation_types[op.type],
		}
	})
})

const Element = (_: any, { slots }: any) => {
	return (
		<div class="w-fit truncate rounded border border-orange-200 bg-orange-50 px-1 py-0.5 font-mono text-xs text-orange-800 opacity-90">
			{slots.default?.()}
		</div>
	)
}

const getQueryTitle = (query_name: string) => {
	const q = useQuery(query_name)
	return q ? q.doc.title : query_name
}

const SourceInfo = (props: any) => {
	const source = props.source as Source
	const source_name =
		source.table.type === 'table'
			? source.table.table_name
			: getQueryTitle(source.table.query_name)
	const is_table = source.table.type === 'table'

	return (
		<div class="flex items-baseline gap-1 text-gray-700">
			<p>Select</p>
			<Element>{source_name}</Element>
			<p>{is_table ? 'table' : 'query'}</p>
		</div>
	)
}

const JoinInfo = (props: any) => {
	const join = props.join as Join
	const join_type = join.join_type
	const join_name =
		join.table.type === 'table' ? join.table.table_name : getQueryTitle(join.table.query_name)
	const is_table = join.table.type === 'table'

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<Element>{join_type}</Element>
			<p>join</p>
			<Element>{join_name}</Element>
			<p>{is_table ? 'table' : 'query'}</p>
		</div>
	)
}

const UnionInfo = (props: any) => {
	const union = props.union as Union
	const union_name =
		union.table.type === 'table'
			? union.table.table_name
			: getQueryTitle(union.table.query_name)

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Append</p>
			<Element>{union_name}</Element>
			<p>table</p>
		</div>
	)
}

const SelectInfo = (props: any) => {
	const select = props.select as Select
	const column_names = select.column_names

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Select</p>
			<Element>{column_names.length} columns</Element>
		</div>
	)
}

const RemoveInfo = (props: any) => {
	const remove = props.remove as Remove
	const column_names = remove.column_names

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Remove</p>
			<Element>{column_names.length} columns</Element>
		</div>
	)
}

const RenameInfo = (props: any) => {
	const rename = props.rename as Rename
	const column_name = rename.column.column_name
	const new_name = rename.new_name

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Rename</p>
			<Element>{column_name}</Element>
			<p>to</p>
			<Element>{new_name}</Element>
		</div>
	)
}

const CastInfo = (props: any) => {
	const cast = props.cast as Cast
	const column_name = cast.column.column_name
	const new_type = cast.data_type

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Convert</p>
			<Element>{column_name}</Element>
			<p>to</p>
			<Element>{new_type}</Element>
		</div>
	)
}

const FilterInfo = (props: any) => {
	const group = props.filter as FilterGroup
	const custom_expressions = group.filters.filter(
		(f) => 'expression' in f && f.expression.expression,
	)
	const filtered_columns = group.filters
		.filter((f) => 'column' in f)
		.map((f) => f.column.column_name)

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Filter</p>
			{filtered_columns.map((column, idx) => (
				<Element>{column}</Element>
			))}
			{custom_expressions.map((expression, idx) => (
				<Element>expression</Element>
			))}
		</div>
	)
}

const MutateInfo = (props: any) => {
	const mutate = props.mutate as Mutate
	const column_name = mutate.new_name

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Calculate</p>
			<Element>{column_name}</Element>
		</div>
	)
}

const SummarizeInfo = (props: any) => {
	const summarize = props.summarize as Summarize
	const measures = summarize.measures
	const dimensions = summarize.dimensions

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Summarize</p>
			{measures.map((measure, idx) => (
				<Element>{measure.measure_name}</Element>
			))}
			<p>by</p>
			{dimensions.map((dimension, idx) => (
				<Element>{dimension.column_name}</Element>
			))}
		</div>
	)
}

const OrderByInfo = (props: any) => {
	const sort = props.sort as OrderBy
	const column_name = sort.column.column_name
	const sort_order = sort.direction

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Sort</p>
			<Element>{column_name}</Element>
			<p>{sort_order}</p>
		</div>
	)
}

const LimitInfo = (props: any) => {
	const limit = props.limit as Limit
	const limit_value = limit.limit

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Limit to</p>
			<Element>{limit_value}</Element>
			<p>rows</p>
		</div>
	)
}

const CustomOperationInfo = (props: any) => {
	const custom_operation = props.custom_operation as CustomOperation

	return (
		<div class="flex flex-wrap items-baseline gap-1 text-gray-700">
			<p>Apply</p>
			<Element>{custom_operation.expression.expression}</Element>
		</div>
	)
}
</script>

<template>
	<div v-if="query.doc.operations.length" class="flex w-full flex-col px-3.5 py-3">
		<div class="mb-2 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm font-medium">Operations</div>
			</div>
			<div></div>
		</div>
		<div class="relative ml-3 flex flex-col-reverse gap-3 border-l border-gray-300 text-sm">
			<template v-for="(op, idx) in operations" :key="idx">
				<div
					class="group relative flex cursor-pointer select-none items-start gap-2"
					:class="idx <= query.activeOperationIdx ? 'opacity-100' : 'opacity-40'"
					@click="query.setActiveOperation(idx)"
					@dblclick="query.setActiveEditIndex(idx)"
				>
					<div
						class="-ml-[14px] h-fit flex-shrink-0 rounded border border-gray-400 bg-white p-1"
					>
						<component
							:is="op.meta.icon"
							class="h-4 w-4 text-gray-600"
							stroke-width="1.5"
						/>
					</div>
					<div
						class="flex flex-1 items-center justify-between gap-2 overflow-hidden pt-1"
					>
						<div class="flex flex-1 flex-col gap-1 overflow-hidden">
							<SourceInfo v-if="op.type === 'source'" :source="op" />
							<JoinInfo v-else-if="op.type === 'join'" :join="op" />
							<UnionInfo v-else-if="op.type === 'union'" :union="op" />
							<SelectInfo v-else-if="op.type === 'select'" :select="op" />
							<RemoveInfo v-else-if="op.type === 'remove'" :remove="op" />
							<CastInfo v-else-if="op.type === 'cast'" :cast="op" />
							<RenameInfo v-else-if="op.type === 'rename'" :rename="op" />
							<FilterInfo v-else-if="op.type === 'filter_group'" :filter="op" />
							<MutateInfo v-else-if="op.type === 'mutate'" :mutate="op" />
							<SummarizeInfo v-else-if="op.type === 'summarize'" :summarize="op" />
							<OrderByInfo v-else-if="op.type === 'order_by'" :sort="op" />
							<LimitInfo v-else-if="op.type === 'limit'" :limit="op" />
							<CustomOperationInfo
								v-else-if="op.type === 'custom_operation'"
								:custom_operation="op"
							/>
						</div>
						<div
							v-if="
								query.activeOperationIdx === idx ||
								(query.activeEditIndex === -1 &&
									idx === query.doc.operations.length - 1)
							"
							class="absolute right-0 flex h-full flex-shrink-0 items-center bg-white opacity-0 transition-all group-hover:opacity-100"
						>
							<Button
								variant="ghost"
								@click.prevent.stop="query.removeOperation(idx)"
							>
								<template #icon>
									<XIcon class="h-3.5 w-3.5 text-gray-500" />
								</template>
							</Button>
						</div>
					</div>
				</div>
				<AddOperationPopover v-if="idx === query.activeOperationIdx" />
			</template>
		</div>
	</div>
</template>
