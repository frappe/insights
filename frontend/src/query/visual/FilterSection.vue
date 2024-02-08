<script setup>
import { ListFilter } from 'lucide-vue-next'
import { computed, inject, nextTick, ref } from 'vue'
import FilterEditor from './FilterEditor.vue'
import FilterListItem from './FilterListItem.vue'
import SectionHeader from './SectionHeader.vue'

const query = inject('query')
const assistedQuery = inject('assistedQuery')

const filters = computed(() => assistedQuery.filters)
const activeFilterIdx = ref(null)

const showExpressionEditor = computed(() => {
	if (activeFilterIdx.value === null) return false
	const activeFilter = filters.value[activeFilterIdx.value]
	if (!activeFilter) return false
	return (
		activeFilter.expression.hasOwnProperty('raw') ||
		activeFilter.expression.hasOwnProperty('ast')
	)
})

function onAddFilter() {
	assistedQuery.addFilter()
	nextTick(() => {
		activeFilterIdx.value = filters.value.length - 1
	})
}
function onRemoveFilter() {
	assistedQuery.removeFilterAt(activeFilterIdx.value)
	activeFilterIdx.value = null
}
function onSaveFilter(filter) {
	assistedQuery.updateFilterAt(activeFilterIdx.value, filter)
	activeFilterIdx.value = null
}
</script>

<template>
	<div class="space-y-2">
		<SectionHeader
			title="Filters"
			:icon="ListFilter"
			info="Apply filters to narrow down the results."
		>
			<Button variant="outline" icon="plus" @click.prevent.stop="onAddFilter"></Button>
		</SectionHeader>
		<div class="space-y-2" v-if="filters.length">
			<template v-for="(filter, idx) in filters" :key="idx">
				<Popover
					:show="activeFilterIdx === idx"
					@close="activeFilterIdx === idx ? (activeFilterIdx = null) : null"
					placement="right-start"
				>
					<template #target="{ togglePopover }">
						<FilterListItem
							:filter="filter"
							:isActive="activeFilterIdx === idx"
							@edit="activeFilterIdx = idx"
							@remove="assistedQuery.removeFilterAt(idx)"
						/>
					</template>
					<template #body>
						<div
							v-if="activeFilterIdx === idx"
							class="ml-2 min-w-[20rem] rounded-lg border border-gray-100 bg-white text-base shadow-xl transition-all"
						>
							<FilterEditor
								:filter="filters[activeFilterIdx]"
								@discard="activeFilterIdx = null"
								@remove="onRemoveFilter"
								@save="onSaveFilter"
							/>
						</div>
					</template>
				</Popover>
			</template>
		</div>
	</div>
</template>
