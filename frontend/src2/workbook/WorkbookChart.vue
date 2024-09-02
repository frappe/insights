<script setup lang="ts">
import { computed, inject } from 'vue'
import ChartBuilder from '../charts/ChartBuilder.vue'
import { Workbook, workbookKey } from './workbook'

const props = defineProps<{ name?: string; index: number | string }>()

const workbook = inject(workbookKey) as Workbook
const activeChart = computed(() => workbook.doc.charts[Number(props.index)])
</script>

<template>
	<ChartBuilder
		v-if="activeChart"
		:key="activeChart.name"
		:chart="activeChart"
		:queries="workbook.doc.queries"
	/>
</template>
