<script setup lang="ts">
import { CircleDotIcon, Edit, Sparkles, XIcon } from 'lucide-vue-next'
import { inject } from 'vue'
import { query_operation_types } from '../helpers'
import { Query } from '../query'

const query = inject('query') as Query
</script>

<template>
	<div v-if="query.doc.operations.length" class="flex flex-col px-2.5 py-2">
		<div class="mb-1 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm font-medium">Operations</div>
			</div>
			<div></div>
		</div>
		<div class="relative ml-1.5 mt-1 border-l border-gray-300 text-xs">
			<div
				v-for="(op, idx) in query.doc.operations"
				:key="idx"
				class="group relative ml-3 mb-3 cursor-pointer last:mb-0"
				:class="idx <= query.activeOperationIdx ? 'opacity-100' : 'opacity-40'"
				@click="query.setActiveOperation(idx)"
			>
				<CircleDotIcon class="absolute -left-4 top-1 h-2 w-2 bg-white text-gray-600" />
				<div class="flex items-center justify-between gap-2 overflow-hidden">
					<div class="flex flex-1 flex-col gap-1 overflow-hidden">
						<div class="font-medium text-gray-900">
							{{ query_operation_types[op.type].label }}
						</div>
						<div class="text-gray-700" data-state="closed">
							{{ query_operation_types[op.type].getDescription(op as any) }}
						</div>
					</div>
					<div
						v-show="
							query.activeOperationIdx === idx ||
							(query.activeEditIndex === -1 &&
								idx === query.doc.operations.length - 1)
						"
						class="flex-shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
					>
						<Button variant="ghost" @click.prevent.stop="query.setActiveEditIndex(idx)">
							<template #icon>
								<Edit class="h-3.5 w-3.5 text-gray-500" />
							</template>
						</Button>
						<Button variant="ghost" @click.prevent.stop="query.removeOperation(idx)">
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
