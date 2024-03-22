<script setup lang="ts">
import { inject } from 'vue'
import QueryPipelineStep from './QueryPipelineStep.vue'
import { QueryPipeline } from './useQueryPipeline'

const queryPipeline = inject('queryPipeline') as QueryPipeline
</script>

<template>
	<div v-if="queryPipeline.steps.length" class="flex flex-col p-1">
		<div
			v-for="(step, idx) in queryPipeline.steps"
			:key="idx"
			class="group flex cursor-pointer items-center justify-between gap-2 rounded border border-transparent p-0.5 pl-1 transition-all hover:border-gray-500"
			:class="idx <= queryPipeline.activeStepIndex ? 'opacity-100' : 'opacity-30'"
		>
			<QueryPipelineStep :step="step" />
			<div class="invisible flex gap-2 group-hover:visible">
				<Button icon="play" variant="ghost" @click="queryPipeline.execute(idx)" />
			</div>
		</div>
	</div>
</template>
