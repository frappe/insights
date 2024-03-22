<script setup lang="ts">
import { inject, ref } from 'vue'
import QueryPipelineSteps from './QueryPipelineSteps.vue'
// import queryPipelineExample from './pipeline_example';
import { Columns2, GanttChartIcon } from 'lucide-vue-next'
import { QueryPipeline } from './useQueryPipeline'

const queryPipeline = inject('queryPipeline') as QueryPipeline

const currentTab = ref('Operations')
const tabs = [
	{ label: 'Data', icon: Columns2 },
	{ label: 'Operations', icon: GanttChartIcon },
]
</script>

<template>
	<div class="flex h-full flex-col">
		<div class="border-b">
			<Button
				v-for="(tab, idx) in tabs"
				:key="idx"
				class="rounded-none"
				:class="{ 'border-b-2 border-gray-700': currentTab === tab.label }"
				size="lg"
				variant="ghost"
			>
				<template #icon>
					<component :is="tab.icon" class="h-5 w-5 text-gray-700" stroke-width="1.5" />
				</template>
				<!-- <span>{{ tab.label }}</span> -->
			</Button>
		</div>
		<div class="flex h-full flex-col gap-1 overflow-y-scroll">
			<QueryPipelineSteps v-if="currentTab === 'Operations'" />
		</div>
	</div>
</template>
