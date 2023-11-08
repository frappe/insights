<template>
	<div class="flex items-center justify-between rounded-b-md px-1 text-base">
		<div v-if="orderByColumns.length" class="flex items-center space-x-1">
			<span class="text-gray-600">Sorted by</span>
			<div class="flex items-center space-x-1">
				<span
					v-for="(column, index) in orderByColumns"
					:key="index"
					class="flex items-center space-x-1 font-medium"
				>
					<span>{{ column.label }}</span>
					<span class="text-gray-600">{{ getOrder(column.label) }}</span>
					<span v-if="index < orderByColumns.length - 1" class="text-gray-600">,</span>
				</span>
			</div>
		</div>
		<div class="ml-auto flex items-center space-x-1">
			<span class="text-gray-600">Limit to</span>
			<input
				type="text"
				ref="limitInput"
				v-model.number="limit"
				:size="String(limit).length"
				class="form-input"
				@keydown.enter.stop="onLimitChange()"
				@keydown.esc.stop="$refs.limitInput.blur()"
			/>
			<span class="text-gray-600">rows</span>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue'

const builder = inject('builder')
const limit = ref(builder.query.limit)
const orderByColumns = computed(() => {
	return builder.query.columns.filter((c) => c.order)
})
function getOrder(columnLabel) {
	return builder.query.columns.find((c) => c.label == columnLabel)?.order
}
const limitInput = ref(null)
function onLimitChange() {
	builder.query.limit = limit
	limitInput.value.blur()
}
</script>
