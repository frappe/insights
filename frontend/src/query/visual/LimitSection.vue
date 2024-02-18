<script setup>
import { watchDebounced } from '@vueuse/core'
import { Infinity } from 'lucide-vue-next'
import { inject, ref, watch } from 'vue'
import SectionHeader from './SectionHeader.vue'

const assistedQuery = inject('assistedQuery')
const limit = ref(assistedQuery.limit)
watchDebounced(limit, assistedQuery.setLimit, { debounce: 300 })
watch(
	() => assistedQuery.limit,
	(val) => (limit.value = val)
)
</script>

<template>
	<div>
		<SectionHeader
			:icon="Infinity"
			title="Row Limit"
			info="Limit the number of rows returned by the query"
		>
			<input
				type="text"
				ref="limitInput"
				v-model.number="limit"
				:size="String(limit).length"
				class="tnum form-input rounded border border-gray-300 bg-white pr-1.5 text-gray-800 placeholder-gray-500 transition-colors hover:border-gray-400 hover:bg-white"
			/>
		</SectionHeader>
	</div>
</template>
