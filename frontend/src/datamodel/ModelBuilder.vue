<script setup lang="tsx">
import QueryBuilder from '@/query/next/QueryBuilder.vue'
import { ChevronDown } from 'lucide-vue-next'
import useDataModel, { DataModel } from './useDataModel'

type ModelBuilderProps = { modelName: string } | { model: DataModel }
const props = defineProps<ModelBuilderProps>()
const dataModel = 'model' in props ? props.model : useDataModel(props.modelName)

const sidebarSections = [
	{ title: 'Tables', items: [], itemComponent: 'div' },
	{ title: 'Relationships', items: [] },
	{ title: 'Dimensions', items: [] },
	{ title: 'Measures', items: [] },
]
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="flex h-full w-full flex-col overflow-hidden pt-0 pr-0">
			<QueryBuilder :query="dataModel.query" />
		</div>

		<div v-if="false" class="relative flex w-[18rem] flex-shrink-0 flex-col bg-white">
			<div
				v-for="section in sidebarSections"
				:key="section.title"
				class="flex flex-col gap-2 p-3"
			>
				<div class="flex cursor-pointer items-center gap-1">
					<div class="text-[11px] uppercase text-gray-600">{{ section.title }}</div>
					<ChevronDown class="h-4 w-4 text-gray-600" stroke-width="1.5" />
				</div>
				<div v-if="section.items.length" class="flex flex-col">
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
		</div>
	</div>
</template>
