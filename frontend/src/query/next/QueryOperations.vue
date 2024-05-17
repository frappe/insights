<script setup lang="ts">
import { ChevronDown, CircleDotIcon, XIcon } from 'lucide-vue-next'
import { inject } from 'vue'
import { query_operation_types } from './query_utils'
import { Query } from './useQuery'

const query = inject('query') as Query
</script>

<template>
	<div v-if="query.operations.length" class="flex flex-col gap-2 p-2.5">
		<div class="flex cursor-pointer items-center gap-1">
			<div class="text-[11px] font-medium uppercase">Query Operations</div>
		</div>
		<div class="relative ml-1.5 mt-1 border-l border-gray-300 font-mono text-xs">
			<div
				v-for="(op, idx) in query.operations"
				:key="idx"
				class="group relative ml-3 mb-3 cursor-pointer last:mb-0"
				:class="idx <= query.activeOperationIdx ? 'opacity-100' : 'opacity-40'"
				@click="query.setActiveStep(idx)"
			>
				<CircleDotIcon class="absolute -left-4 top-0.5 h-2 w-2 bg-white text-gray-600" />
				<div class="flex items-center justify-between gap-2 overflow-hidden">
					<div class="flex flex-1 flex-col gap-1 overflow-hidden">
						<div class="font-medium text-gray-900">
							{{ query_operation_types[op.type].label }}
						</div>
						<div class="text-gray-700" data-state="closed">
							{{ query_operation_types[op.type].getDescription(op as any) }}
						</div>
					</div>
					<div class="flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100">
						<Button variant="ghost" @click="query.removeStep(idx)">
							<template #icon>
								<XIcon class="h-3.5 w-3.5 text-gray-500" />
							</template>
						</Button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
