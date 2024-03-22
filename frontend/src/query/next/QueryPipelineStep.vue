<script setup lang="ts">
import { PropType } from 'vue'
import { pipeline_step_types } from './pipeline_utils'

const props = defineProps({
	step: {
		type: Object as PropType<PipelineStep>,
		required: true,
	},
})
const step_option = pipeline_step_types[props.step.type]
</script>

<template>
	<div class="font-code flex w-full items-center gap-2 overflow-hidden">
		<div class="flex items-center justify-center rounded p-1.5" :class="step_option.class">
			<component :is="step_option.icon" class="h-3.5 w-3.5" />
		</div>
		<p class="truncate">
			{{ step_option.getStepLabel(props.step as any) }}
		</p>
	</div>
</template>
