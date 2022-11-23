<script setup>
import { inject } from 'vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import InputWithTabs from '@/components/Controls/InputWithTabs.vue'

const query = inject('query')
const chart = inject('chart')
if (!chart.config.targetType) {
	chart.config.targetType = 'Column'
}
if (chart.config.targetColumn) {
	// for backward compatibility
	chart.config.target = chart.config.target || chart.config.targetColumn
}
</script>

<template>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Progress</div>
		<Autocomplete v-model="chart.config.progressColumn" :options="query.results.valueOptions" />
	</div>
	<div class="space-y-2 text-gray-600">
		<div class="text-base font-light text-gray-500">Target</div>
		<InputWithTabs
			:value="chart.config.target"
			:tabs="{
				Column: chart.config.targetType === 'Column',
				Value: chart.config.targetType === 'Value',
			}"
			@tab-change="chart.config.targetType = $event"
		>
			<template #inputs>
				<div class="w-full">
					<Autocomplete
						v-if="chart.config.targetType === 'Column'"
						v-model="chart.config.target"
						placeholder="Select a column..."
						:options="query.results.valueOptions"
					/>
					<Input
						v-if="chart.config.targetType === 'Value'"
						v-model="chart.config.target"
						placeholder="Enter a value..."
						type="number"
						class="h-8"
					/>
				</div>
			</template>
		</InputWithTabs>
	</div>
	<div class="space-y-3 text-sm text-gray-600">
		<div class="space-y-1">
			<div class="font-light">Prefix</div>
			<Input type="text" v-model="chart.options.prefix" placeholder="Enter a prefix..." />
		</div>
		<div class="space-y-1">
			<div class="font-light">Suffix</div>
			<Input type="text" v-model="chart.options.suffix" placeholder="Enter a suffix..." />
		</div>
		<div class="space-y-1">
			<div class="font-light">Decimals</div>
			<Input type="number" v-model="chart.options.decimals" placeholder="Enter a number..." />
		</div>

		<div class="space-y-2 text-gray-600">
			<Checkbox v-model="chart.options.shorten" label="Shorten Numbers" />
		</div>
	</div>
</template>
