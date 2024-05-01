<script setup lang="tsx">
import QueryBuilder from '@/query/next/QueryBuilder.vue'
import { provide } from 'vue'
import ModelSidebar from './ModelSidebar.vue'
import useDataModel, { DataModel, dataModelKey } from './useDataModel'

type ModelBuilderProps = { modelName: string } | { model: DataModel }
const props = defineProps<ModelBuilderProps>()
const dataModel = 'model' in props ? props.model : useDataModel(props.modelName)
provide(dataModelKey, dataModel)
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div class="flex h-full w-full flex-col overflow-hidden pt-0 pr-0">
			<QueryBuilder :query="dataModel.activeQuery" />
		</div>

		<div v-if="true" class="relative flex w-[18rem] flex-shrink-0 flex-col bg-white">
			<ModelSidebar />
		</div>
	</div>
</template>
