<script setup lang="ts">
import { Analysis, analysisKey } from '@/analysis/useAnalysis'
import { fieldtypesToIcon } from '@/utils'
import { XIcon } from 'lucide-vue-next'
import { inject } from 'vue'
import { AnalysisQuery, analysisQueryKey } from '../useAnalysisQuery'

const analysis = inject(analysisKey) as Analysis
if (!analysis) throw new Error('Analysis not found')

const analysisQuery = inject(analysisQueryKey) as AnalysisQuery
if (!analysisQuery) throw new Error('AnalysisQuery not found')
</script>

<template>
	<div class="relative flex w-[16rem] flex-shrink-0 flex-col overflow-y-auto bg-white">
		<!-- dimensions -->
		<div class="flex flex-col gap-2 p-3">
			<div class="text-[11px] uppercase text-gray-600">Dimensions</div>
			<div class="flex flex-col gap-1 font-mono">
				<Button
					variant="outline"
					v-for="dimension in analysis.model.dimensions"
					:key="dimension.column_name"
					class="!justify-start"
					@click="analysisQuery.addDimension(dimension)"
				>
					<div class="flex items-center gap-2">
						<component
							:is="fieldtypesToIcon[dimension.data_type]"
							class="h-4 w-4 text-gray-600"
							stroke-width="1.5"
						></component>
						<div class="text-xs">{{ dimension.column_name }}</div>
					</div>
				</Button>
			</div>
		</div>
		<!-- measures -->
		<div class="flex flex-col gap-2 p-3">
			<div class="text-[11px] uppercase text-gray-600">Measures</div>
			<div class="flex flex-col gap-1 font-mono">
				<Button
					variant="outline"
					v-for="measure in analysis.model.measures"
					:key="measure.column_name"
					class="!justify-start"
					@click="analysisQuery.addMeasure(measure)"
				>
					<div class="flex items-center gap-2">
						<component
							:is="fieldtypesToIcon[measure.data_type]"
							class="h-4 w-4 text-gray-600"
							stroke-width="1.5"
						></component>
						<div class="text-xs">
							{{ measure.aggregation.toUpperCase() }}({{ measure.column_name }})
						</div>
					</div>
				</Button>
			</div>
		</div>
		<hr class="my-1 border-t border-gray-200" />
		<div class="flex flex-col gap-2 p-3">
			<div class="text-[11px] uppercase text-gray-600">Rows</div>
			<div class="flex min-h-[5rem] flex-col gap-1 rounded border bg-gray-50 p-1 font-mono">
				<div
					v-for="dimension in analysisQuery.dimensions"
					:key="dimension.column_name"
					class="flex h-6 items-center gap-2 rounded bg-white px-2 shadow"
				>
					<component
						:is="fieldtypesToIcon[dimension.data_type]"
						class="h-3.5 w-3.5 text-gray-600"
						stroke-width="1.5"
					></component>
					<div class="text-xs">{{ dimension.column_name }}</div>
					<XIcon
						class="ml-auto h-3.5 w-3.5 cursor-pointer text-gray-500 hover:text-gray-700"
						@click="analysisQuery.remove(dimension)"
					/>
				</div>
			</div>
		</div>
		<div class="flex flex-col gap-2 p-3">
			<div class="text-[11px] uppercase text-gray-600">Columns</div>
			<div class="flex min-h-[5rem] gap-1 rounded border bg-gray-50 font-mono"></div>
		</div>
		<div class="flex flex-col gap-2 p-3">
			<div class="text-[11px] uppercase text-gray-600">Values</div>
			<!-- list all the measures -->
			<div class="flex min-h-[5rem] flex-col gap-1 rounded border bg-gray-50 p-1 font-mono">
				<div
					v-for="measure in analysisQuery.measures"
					:key="measure.column_name"
					class="flex h-6 items-center gap-2 rounded bg-white px-2 shadow"
				>
					<component
						:is="fieldtypesToIcon[measure.data_type]"
						class="h-3.5 w-3.5 text-gray-600"
						stroke-width="1.5"
					></component>
					<div class="text-xs">
						{{ measure.aggregation.toUpperCase() }}({{ measure.column_name }})
					</div>
					<XIcon
						class="ml-auto h-3.5 w-3.5 cursor-pointer text-gray-500 hover:text-gray-700"
						@click="analysisQuery.remove(measure)"
					/>
				</div>
			</div>
		</div>
	</div>
</template>
