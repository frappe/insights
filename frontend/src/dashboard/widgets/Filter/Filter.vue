<script setup>
import SimpleFilter from '@/dashboard/SimpleFilter.vue'
import { getLocal, saveLocal } from 'frappe-ui/src/resources/local'
import { inject, ref } from 'vue'

const props = defineProps({
	item_id: { required: true },
	options: { type: Object, required: true },
})

const dashboard = inject('dashboard')
const filterStateKey = `filterState-${dashboard.doc.name}-${props.item_id}`

const filterState = ref(undefined)
getLocal(filterStateKey).then((state) => {
	if (state) filterState.value = state
})
function saveFilterState(state) {
	filterState.value = state
		? {
				operator: state.operator,
				value: state.value,
		  }
		: undefined
	saveLocal(filterStateKey, filterState.value).then(() => {
		dashboard.refreshFilter(props.item_id)
	})
}
</script>

<template>
	<div class="flex w-full items-center" :class="[!filterState?.operator ? '!text-gray-500' : '']">
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
