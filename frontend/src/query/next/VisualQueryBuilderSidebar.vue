<script setup lang="ts">
import { ArrowUpDown, Combine, Filter, Indent, Merge, Sigma, Table } from 'lucide-vue-next'
import { h, inject } from 'vue'
import queryPipelineExample from './pipeline_example'
import { QueryPipeline } from './useQueryPipeline'

console.log(queryPipelineExample.steps.value)

const queryPipeline = inject('queryPipeline') as QueryPipeline
queryPipeline.setPipeline(queryPipelineExample.steps.value)

const pipelineStepOptions = {
	source: {
		label: 'From',
		icon: getIconComponent(Table, 'text-blue-500', 'bg-blue-100'),
		getValueLabel(step: Source) {
			return step.table.table_name
		},
	},
	join: {
		label: 'Join',
		icon: getIconComponent(Merge, 'text-teal-500', 'bg-teal-100'),
		getValueLabel(step: Join) {
			return step.table.table_name
		},
	},
	filter: {
		label: 'Filter',
		icon: getIconComponent(Filter, 'text-yellow-500', 'bg-yellow-100'),
		getValueLabel(step: Filter) {
			const val = typeof step.value === 'object' ? step.value.column_name : step.value
			return `${step.column.column_name} ${step.operator} ${val}`
		},
	},
	mutate: {
		label: 'Calculate',
		icon: getIconComponent(Sigma, 'text-teal-500', 'bg-teal-100'),
		getValueLabel(step: Mutate) {
			return step.label
		},
	},
	summarize: {
		label: 'Summarize',
		icon: getIconComponent(Combine, 'text-purple-500', 'bg-purple-100'),
		getValueLabel(step: Summarize) {
			return (
				Object.keys(step.metrics).join(', ') +
				'<br> by ' +
				step.by.map((c) => c.column_name).join(', ')
			)
		},
	},
	order_by: {
		label: 'Sort',
		icon: getIconComponent(ArrowUpDown, 'text-orange-500', 'bg-orange-100'),
		getValueLabel(step: OrderBy) {
			return step.column.column_name + ' ' + step.direction
		},
	},
	limit: {
		label: 'Limit',
		icon: getIconComponent(Indent, 'text-pink-500 transform rotate-180', 'bg-pink-100'),
		getValueLabel(args: Limit) {
			return `Limit: ${args.limit}`
		},
	},
	pivot_wider: {
		label: 'Pivot',
		icon: getIconComponent(Indent, 'text-pink-500 transform rotate-180', 'bg-pink-100'),
		getValueLabel(step: PivotWider) {
			return 'Pivot'
		},
	},
}

function getIconComponent(icon: typeof Indent, iconClass: string, backgroundColor: string) {
	return h(
		'div',
		{ class: 'rounded p-1 ' + backgroundColor },
		h(icon, { class: 'h-4 w-4 ' + iconClass })
	)
}

function getIcon(step: any) {
	const stepType = step.type as keyof typeof pipelineStepOptions
	return pipelineStepOptions[stepType].icon
}
function getLabel(step: any) {
	const stepType = step.type as keyof typeof pipelineStepOptions
	return pipelineStepOptions[stepType].getValueLabel(step)
}
</script>

<template>
	<div class="flex items-center justify-between border-b py-1 px-3">
		<p class="text-sm uppercase">Query</p>
		<div class="-mr-2 flex gap-2">
			<Button
				icon="play"
				variant="ghost"
				:loading="queryPipeline.executing.value"
				@click="queryPipeline.execute"
			/>
			<Dropdown
				:button="{ icon: 'plus', variant: 'ghost' }"
				:options="Object.values(pipelineStepOptions)"
			>
			</Dropdown>
		</div>
	</div>
	<div class="flex flex-col gap-1">
		<div v-if="queryPipeline.steps.value.length" class="flex flex-col p-1">
			<div
				v-for="(step, idx) in queryPipeline.steps.value"
				:key="idx"
				class="group flex cursor-pointer items-center justify-between gap-2 rounded border border-transparent p-0.5 pl-1 transition-all hover:border-gray-500"
				:class="idx <= queryPipeline.activeStepIndex.value ? 'opacity-100' : 'opacity-30'"
			>
				<div class="flex items-center gap-2">
					<component :is="getIcon(step)" />
					<div class="text-base" v-html="getLabel(step)"></div>
				</div>
				<div class="invisible flex gap-2 group-hover:visible">
					<Button icon="play" variant="ghost" @click="queryPipeline.execute(idx)" />
				</div>
			</div>
		</div>
	</div>
</template>
