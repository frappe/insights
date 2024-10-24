<script setup lang="ts">
import { call } from 'frappe-ui'
import { ref } from 'vue'
import useQuery from '../query/query'
import { transformWorkbook } from '../workbook/workbook'
import useChart, { Chart } from './chart'
import ChartRenderer from './components/ChartRenderer.vue'

const props = defineProps<{ chart_name: string }>()

const chart = ref<Chart | null>(null)
</script>

<template>
	<div class="h-full w-full">
		<ChartRenderer v-if="chart" :chart="chart" />
	</div>
</template>
