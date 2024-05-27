<script setup lang="tsx">
import { Table2Icon, XIcon } from 'lucide-vue-next'
import { inject } from 'vue'
import { DataModel, dataModelKey } from './useDataModel'

const dataModel = inject(dataModelKey) as DataModel
</script>

<template>
	<div class="flex flex-col gap-2 p-2.5">
		<div class="flex justify-between">
			<div class="flex cursor-pointer items-center gap-1">
				<div class="text-[11px] font-medium uppercase">Queries</div>
			</div>
		</div>
		<div class="flex flex-col text-xs">
			<div
				v-if="dataModel.queries.length"
				v-for="query in dataModel.queries"
				:key="query.name"
				class="group relative"
			>
				<Button
					variant="outline"
					class="w-full !justify-start font-mono !text-xs"
					:class="
						dataModel.activeQuery.name === query.name
							? 'border-gray-400 hover:border-gray-400'
							: 'border-transparent hover:border-transparent'
					"
					@click="dataModel.setActiveQuery(query.name)"
				>
					<template #prefix>
						<Table2Icon class="h-3.5 w-3.5 text-gray-600" :stroke-width="1.5" />
					</template>
					{{ (query.operations[0] as Source)?.table.table_name || query.name }}
				</Button>
				<div
					class="absolute right-0 top-0 z-10 cursor-pointer p-1.5 text-gray-500 transition-all hover:text-gray-700"
				>
					<XIcon class="h-4 w-4" @click="dataModel.removeQuery(query.name)" />
				</div>
			</div>
			<div
				v-else
				class="flex h-12 flex-col items-center justify-center rounded border border-dashed border-gray-300 py-2"
			>
				<div class="text-xs text-gray-500">No queries</div>
			</div>
			<Button
				variant="outline"
				class="mt-2 !border-dashed font-mono !text-xs"
				@click="dataModel.addQuery()"
			>
				Add Query
			</Button>
		</div>
	</div>
	<hr class="mt-1 border-t border-gray-200" />
</template>
