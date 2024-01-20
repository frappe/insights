<script setup>
import SimpleFilter from '@/dashboard/SimpleFilter.vue'
import { computed, inject, provide } from 'vue'

const props = defineProps({
	item_id: { required: true },
	options: { type: Object, required: true },
})
provide('item_id', props.item_id)

const dashboard = inject('dashboard')
const filterState = computed(() => dashboard.filterStates[props.item_id])
function saveFilterState(state) {
	dashboard.setFilterState(props.item_id, state)
}
</script>

<template>
	<div class="flex w-full items-center" :class="[!filterState?.operator ? '!text-gray-600' : '']">
		<SimpleFilter
			:disable-columns="true"
			:label="props.options.label"
			:column="props.options.column"
			:operator="filterState?.operator"
			:value="filterState?.value"
			@apply="saveFilterState"
			@reset="saveFilterState"
		></SimpleFilter>
	</div>
</template>
