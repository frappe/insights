<script setup lang="ts">
import { inject } from 'vue'
import ChartBuilder from '../charts/ChartBuilder.vue'
import { workbookKey } from './workbook'

const props = defineProps<{ workbook_name?: string; chart_name: string }>()

const workbook = inject(workbookKey)!
</script>

<template>
	<ChartBuilder
		:chart_name="props.chart_name"
		:queries="
			workbook.doc.queries.map((q) => {
				return { label: q.title, value: q.name }
			})
		"
	/>
</template>
