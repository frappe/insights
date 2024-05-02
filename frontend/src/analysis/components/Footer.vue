<script setup lang="ts">
import ContentEditable from '@/components/ContentEditable.vue'
import { BarChartIcon, Box, XIcon } from 'lucide-vue-next'
import { inject } from 'vue'
import { analysisKey } from '../useAnalysis'

const analysis = inject(analysisKey)
</script>

<template>
	<footer
		v-if="analysis"
		class="sticky bottom-0 z-10 flex h-10 w-full flex-shrink-0 items-center divide-x border-t bg-white"
	>
		<div
			class="flex h-full cursor-pointer items-center gap-1.5 border-t-2 px-3 transition-all hover:bg-gray-100"
			:class="analysis.activeTabIdx === -1 ? ' border-t-gray-700' : 'border-t-transparent'"
			@click="analysis?.setCurrentTab(-1)"
		>
			<Box class="h-4 w-4" stroke-width="1.5" />
			<div class="flex h-6 items-center whitespace-nowrap rounded-sm px-0.5 text-base">
				Data
			</div>
		</div>
		<div
			v-for="(chart, idx) in analysis.charts"
			:key="idx"
			class="flex h-full cursor-pointer items-center gap-1.5 border-t-2 px-3 transition-all hover:bg-gray-100"
			:class="analysis.activeTabIdx === idx ? ' border-t-gray-700' : 'border-t-transparent'"
			@click="analysis?.setCurrentTab(idx)"
		>
			<BarChartIcon class="h-4 w-4" stroke-width="1.5" />
			<ContentEditable
				:modelValue="chart.title"
				:disabled="true"
				placeholder="Enter Title"
				class="flex h-6 items-center whitespace-nowrap rounded-sm px-0.5 text-base focus:ring-1 focus:ring-gray-700 focus:ring-offset-1"
			/>
			<div class="transition-colors hover:text-gray-900">
				<XIcon class="h-4 w-4" stroke-width="1.5" @click="analysis?.removeChart(idx)" />
			</div>
		</div>
		<div class="flex h-full w-10 items-center justify-center">
			<Button variant="subtle" icon="plus" @click="analysis?.addChart()"> </Button>
		</div>
	</footer>
</template>
