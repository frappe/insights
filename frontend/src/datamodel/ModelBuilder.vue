<script setup lang="tsx">
import { Analysis, analysisKey } from '@/analysis/useAnalysis'
import QueryBuilder from '@/query/next/QueryBuilder.vue'
import { inject, onMounted, provide, ref } from 'vue'
import ModelQueryList from './ModelQueryList.vue'
import { dataModelKey } from './useDataModel'

const analysis = inject(analysisKey) as Analysis
provide(dataModelKey, analysis.model)

const mounted = ref(false)
onMounted(() => (mounted.value = true))
</script>

<template>
	<div class="relative flex h-full w-full overflow-hidden">
		<div
			id="model-sidebar"
			class="relative flex w-[16rem] flex-shrink-0 flex-col overflow-y-auto border-r bg-white"
		>
			<ModelQueryList />
		</div>
		<div
			v-if="mounted && analysis.model.activeQuery"
			class="flex h-full w-full flex-col overflow-hidden pt-0 pr-0"
		>
			<QueryBuilder
				:key="analysis.model.activeQuery.name"
				:query="analysis.model.activeQuery"
			/>
		</div>
	</div>
</template>
