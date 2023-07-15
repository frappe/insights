<template>
	<div
		class="flex h-full flex-1 items-center justify-between rounded-b-md px-1 text-base text-gray-600"
	>
		<div class="ml-auto text-sm">
			<span>Limit to</span>
			<input
				type="text"
				ref="limitInput"
				v-model.number="limit"
				:size="String(limit).length"
				class="form-input mx-1 bg-gray-100 py-0.5 pl-2 pr-1 font-medium text-gray-600 hover:underline focus:border-transparent focus:bg-gray-200 focus:text-gray-600"
				@keydown.enter.stop="
					() => {
						query.setLimit.submit({ limit: parseInt(limit) })
						$refs.limitInput.blur()
					}
				"
				@keydown.esc.stop="$refs.limitInput.blur()"
			/>
			<span>rows</span>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue'

const query = inject('query')

const limit = ref(query.doc.limit)

const sortedByColumns = computed(() => {
	return query.doc.columns
		.filter((c) => c.order_by)
		.map((c) => ({
			column: c.label,
			order: c.order_by,
		}))
})
</script>
