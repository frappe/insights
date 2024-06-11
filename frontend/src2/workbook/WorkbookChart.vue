<script setup lang="ts">
import { inject } from 'vue'
import ChartBuilder from '../charts/ChartBuilder.vue'
import { Workbook, workbookKey } from './workbook'

const props = defineProps<{ name?: string; index: number | string }>()
const workbook = inject(workbookKey) as Workbook
workbook.setActiveTab('chart', Number(props.index))
</script>

<template>
	<ChartBuilder
		v-if="workbook.activeChart"
		:key="workbook.activeChart.name"
		:chart="workbook.activeChart"
		:queries="workbook.doc.queries"
	/>
</template>
