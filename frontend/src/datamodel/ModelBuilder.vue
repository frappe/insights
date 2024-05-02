<script setup lang="tsx">
import QueryBuilder from '@/query/next/QueryBuilder.vue'
import { onMounted, provide, ref } from 'vue'
import ModelQueryList from './ModelQueryList.vue'
import useDataModel, { DataModel, dataModelKey } from './useDataModel'

type ModelBuilderProps = { modelName: string } | { model: DataModel }
const props = defineProps<ModelBuilderProps>()
const dataModel = 'model' in props ? props.model : useDataModel(props.modelName)
provide(dataModelKey, dataModel)

const mounted = ref(false)
onMounted(() => (mounted.value = true))
</script>

<template>
	<div class="relative flex h-full w-full divide-x overflow-hidden">
		<div
			id="model-sidebar"
			class="relative flex w-[16rem] flex-shrink-0 flex-col overflow-y-auto bg-white"
		>
			<ModelQueryList />
		</div>
		<div v-if="mounted" class="flex h-full w-full flex-col overflow-hidden pt-0 pr-0">
			<QueryBuilder :key="dataModel.activeQuery.name" :query="dataModel.activeQuery" />
		</div>
	</div>
</template>
