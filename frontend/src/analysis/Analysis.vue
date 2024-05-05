<script setup lang="ts">
import ModelBuilder from '@/datamodel/ModelBuilder.vue'
import { provide } from 'vue'
import ChartBuilder from './components/ChartBuilder.vue'
import DashboardBuilder from './components/DashboardBuilder.vue'
import Footer from './components/Footer.vue'
import Header from './components/Header.vue'
import useAnalysis, { analysisKey } from './useAnalysis'

const analysis = useAnalysis('new-analysis-1', 'new-model-1')
provide(analysisKey, analysis)
</script>

<template>
	<div class="flex h-full flex-col">
		<Header />
		<div class="flex-1 overflow-hidden">
			<ModelBuilder v-if="analysis.activeTabIdx === -1" />
			<DashboardBuilder v-else-if="analysis.activeTabIdx === Infinity" />
			<ChartBuilder
				v-else
				:key="analysis.activeTabIdx"
				:chart-name="analysis.charts[analysis.activeTabIdx].name"
			/>
		</div>
		<Footer />
	</div>
</template>
