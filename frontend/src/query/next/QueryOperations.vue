<script setup lang="ts">
import { XIcon } from 'lucide-vue-next'
import { inject } from 'vue'
import { query_operation_types } from './query_utils'
import { Query } from './useQuery'

const query = inject('query') as Query
</script>

<template>
	<div v-if="query.operations.length" class="flex flex-col gap-2 p-3">
		<div class="text-[11px] uppercase text-gray-600">Operations</div>
		<div class="flex flex-col gap-1 font-mono">
			<div
				v-for="(op, idx) in query.operations"
				:key="idx"
				class="group relative flex items-center justify-between"
			>
				<Button
					variant="outline"
					class="w-full !justify-start truncate text-left text-xs"
					:class="idx <= query.activeOperationIdx ? 'opacity-100' : 'opacity-50'"
					@click="query.setActiveStep(idx)"
				>
					{{ query_operation_types[op.type].getLabel(op as any) }}
				</Button>
				<Button
					class="absolute right-0 z-10 !rounded-l-none !border-l-0 opacity-0 transition-all group-hover:opacity-100"
					variant="outline"
					@click="query.removeStep(idx)"
				>
					<template #icon>
						<XIcon class="h-3.5 w-3.5 text-gray-500" />
					</template>
				</Button>
			</div>
		</div>
	</div>
</template>
