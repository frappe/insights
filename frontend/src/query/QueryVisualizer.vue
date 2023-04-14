<template>
	<div v-if="chart.doc" class="flex flex-1 overflow-scroll p-2 pt-3">
		<div class="flex w-full flex-shrink-0 flex-col lg:h-full lg:w-[18rem] lg:pr-4">
			<div class="space-y-4">
				<!-- Widget Options -->
				<Input
					type="select"
					label="Chart Type"
					class="w-full"
					v-model="chart.doc.chart_type"
					:options="chartOptions"
				/>

				<component
					v-if="chart.doc.chart_type"
					:is="widgets.getOptionComponent(chart.doc.chart_type)"
					:key="chart.doc.chart_type"
					v-model="chart.doc.options"
					:columns="query.resultColumns"
				/>
			</div>
		</div>

		<div
			class="relative flex h-full min-h-[30rem] w-full flex-1 flex-col space-y-3 overflow-hidden lg:w-auto"
		>
			<div class="ml-4 flex space-x-2">
				<Button appearance="white" class="shadow-sm" @click="showShareDialog = true">
					Share
				</Button>
			</div>
			<component
				v-if="chart.doc.chart_type"
				ref="widget"
				:is="widgets.getComponent(chart.doc.chart_type)"
				:chartData="{ data: chart.data }"
				:options="chart.doc.options"
				:key="JSON.stringify(chart.doc.options)"
			>
				<template #placeholder>
					<InvalidWidget
						class="absolute"
						title="Insufficient options"
						message="Please check the options for this chart"
						icon="settings"
						icon-class="text-gray-400"
					/>
				</template>
			</component>
		</div>

		<PublicShareDialog
			v-if="chart.doc.doctype && chart.doc.name"
			v-model:show="showShareDialog"
			:resource-type="chart.doc.doctype"
			:resource-name="chart.doc.name"
			:allow-public-access="true"
			:isPublic="Boolean(chart.doc.is_public)"
			@togglePublicAccess="chart.togglePublicAccess"
		/>
	</div>
</template>

<script setup>
import PublicShareDialog from '@/components/PublicShareDialog.vue'
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import widgets from '@/widgets/widgets'
import { inject, ref } from 'vue'
import useChart from './useChart'

const query = inject('query')
const showShareDialog = ref(false)
const chartOptions = [
	{
		label: 'Select a chart type',
		value: undefined,
	},
].concat(widgets.getChartOptions())

let chart = ref({})
query.get_chart_name.submit().then((res) => {
	chart.value = useChart(res.message)
	chart.value.autosave = true
})
</script>
