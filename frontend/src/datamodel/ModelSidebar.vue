<script setup lang="tsx">
import { Query } from '@/query/next/useQuery'
import { BookDashedIcon, ChevronDown, PlusIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import { DataModel, Dimension, Measure, dataModelKey } from './useDataModel'

const dataModel = inject(dataModelKey) as DataModel

type ListItemProps = { item: any }
const QueryListItemComponent = (props: ListItemProps) => {
	const query = props.item as Query
	const sourceStep = query.operations[0] as Source
	const isActive = dataModel.activeQuery === query
	return (
		<div
			class={`flex h-7 w-full cursor-pointer items-center rounded border bg-white px-2 font-mono ${
				isActive ? 'border-gray-800' : ''
			}`}
		>
			{sourceStep.table.table_name}
		</div>
	)
}

const DimensionListItemComponent = (props: ListItemProps) => {
	const dimension = props.item as Dimension
	return (
		<div class="flex w-full items-center gap-1 font-mono text-gray-800">
			<BookDashedIcon class="h-3.5 w-3.5" stroke-width="1.5" />
			<span>{dimension.column_name}</span>
		</div>
	)
}
const MeasureListItemComponent = (props: ListItemProps) => {
	const measure = props.item as Measure
	const agg = measure.aggregation.toUpperCase()
	const col = measure.column_name == 'count' ? '*' : measure.column_name
	const value = dataModel.measureValues[measure.column_name] ?? '...'
	return (
		<div class="flex items-center justify-between font-mono text-gray-800">
			<div class="flex items-center gap-1">
				<BookDashedIcon class="h-3.5 w-3.5" stroke-width="1.5" />
				<span>{`${agg}(${col})`}</span>
			</div>
			<div>{value.toLocaleString()}</div>
		</div>
	)
}

const sidebarSections = ref([
	{
		title: 'Queries',
		singular: 'Query',
		items: computed(() => dataModel.queries),
		itemComponent: QueryListItemComponent,
	},
	{ title: 'Relationships', singular: 'Relationship', items: [] },
	{
		title: 'Dimensions',
		singular: 'Dimension',
		items: computed(() => dataModel.dimensions),
		itemComponent: DimensionListItemComponent,
	},
	{
		title: 'Measures',
		singular: 'Measure',
		items: computed(() => dataModel.measures),
		itemComponent: MeasureListItemComponent,
	},
])
</script>

<template>
	<div v-for="section in sidebarSections" :key="section.title" class="flex flex-col gap-2 p-3">
		<div class="flex justify-between">
			<div class="flex cursor-pointer items-center gap-1">
				<ChevronDown class="h-4 w-4 text-gray-600" stroke-width="1.5" />
				<div class="text-[11px] uppercase text-gray-600">{{ section.title }}</div>
			</div>
			<Tooltip
				:hoverDelay="0.1"
				:text="`Add ${section.singular}`"
				class="cursor-pointer text-gray-600 hover:text-gray-900"
			>
				<PlusIcon class="h-4 w-4" stroke-width="1.5" />
			</Tooltip>
		</div>
		<div v-if="section.items.length" class="flex flex-col gap-2 text-xs">
			<component
				v-for="(item, idx) in section.items"
				:key="idx"
				:is="section.itemComponent"
				:item="item"
			/>
		</div>
		<div
			v-else
			class="flex h-12 flex-col items-center justify-center rounded border border-dashed border-gray-300 py-2"
		>
			<div class="text-xs text-gray-500">No {{ section.title.toLowerCase() }}</div>
		</div>
	</div>
</template>
