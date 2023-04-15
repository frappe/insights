<script setup>
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import widgets from '@/widgets/widgets'

import { inject } from 'vue'
const query = inject('query')
query.loadChart()
</script>

<template>
	<div class="h-full w-full overflow-hidden">
		<component
			v-if="query.chart.doc?.chart_type"
			ref="widget"
			:is="widgets.getComponent(query.chart.doc.chart_type)"
			:chartData="{ data: query.chart.data }"
			:options="query.chart.doc.options"
			:key="JSON.stringify(query.chart.doc.options)"
		>
			<template #placeholder>
				<div class="relative h-full w-full">
					<InvalidWidget
						class="absolute"
						title="Insufficient options"
						message="Please check the options for this chart"
						icon="settings"
						icon-class="text-gray-400"
					/>
				</div>
			</template>
		</component>
	</div>
</template>
