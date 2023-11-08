<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { ListFilter, X } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import FilterEditor from './FilterEditor.vue'

const query = inject('query')
const builder = inject('builder')

const filters = computed(() => builder.query.filters)
const filterRefs = ref(null)
const activeFilterIdx = ref(null)

function onAddFilter() {
	builder.addFilter()
	activeFilterIdx.value = filters.value.length - 1
}
function onRemoveFilter() {
	builder.removeFilterAt(activeFilterIdx.value)
	activeFilterIdx.value = null
}
function onSaveFilter(filter) {
	builder.updateFilterAt(activeFilterIdx.value, filter)
	activeFilterIdx.value = null
}
function isValidFilter(filter) {
	if (filter.expression?.raw && filter.expression?.ast) return true
	return (
		filter.column.column &&
		filter.operator.value &&
		(filter.value.value || filter.operator.value.includes('is_'))
	)
}
</script>

<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<div class="flex items-center space-x-1.5">
				<ListFilter class="h-4 w-4 text-gray-600" />
				<p class="font-medium">Filter</p>
			</div>
			<Button variant="outline" icon="plus" @click.prevent.stop="onAddFilter"></Button>
		</div>
		<div class="space-y-2">
			<div
				ref="filterRefs"
				v-for="(filter, idx) in filters"
				:key="idx"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 hover:shadow"
				@click="activeFilterIdx = filters.indexOf(filter)"
			>
				<div class="flex w-full items-center overflow-hidden">
					<div class="flex w-full space-x-2" v-if="isValidFilter(filter)">
						<template v-if="filter.expression?.raw">
							<span class="truncate font-mono">{{ filter.expression.raw }}</span>
						</template>
						<template v-else>
							<span class="max-w-[30%] flex-shrink-0 truncate">
								{{ filter.column.label || filter.column.column }}
							</span>
							<span class="flex-shrink-0 font-medium text-green-600">
								{{ filter.operator.label || filter.operator.value }}
							</span>
							<span class="flex-1 flex-shrink-0 truncate">
								{{ filter.value.label || filter.value.value }}
							</span>
						</template>
					</div>
					<div v-else class="text-gray-600">Select a filter</div>
				</div>
				<div class="flex items-center">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
						@click.prevent.stop="builder.removeFilterAt(idx)"
					/>
				</div>
			</div>
		</div>
	</div>

	<UsePopover
		v-if="filterRefs?.[activeFilterIdx]"
		:show="activeFilterIdx !== null"
		@update:show="activeFilterIdx = null"
		:target-element="filterRefs[activeFilterIdx]"
	>
		<div class="w-[19rem] rounded bg-white text-base shadow-2xl">
			<FilterEditor
				:filter="filters[activeFilterIdx]"
				@discard="activeFilterIdx = null"
				@remove="onRemoveFilter"
				@save="onSaveFilter"
			/>
		</div>
	</UsePopover>
</template>
