<template>
	<node-view-wrapper class="not-prose text-base">
		<Suspense>
			<ChartBlock
				:chartName="props.node.attrs.chart_name"
				@setChartName="props.updateAttributes({ chart_name: $event })"
				@remove="props.deleteNode()"
			/>
		</Suspense>
	</node-view-wrapper>
</template>

<script setup>
import ChartBlock from '@/notebook/blocks/chart/ChartBlock.vue'
import { NodeViewWrapper, nodeViewProps } from '@tiptap/vue-3'
const props = defineProps(nodeViewProps)
</script>
