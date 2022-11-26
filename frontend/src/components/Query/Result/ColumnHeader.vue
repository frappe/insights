<template>
	<div v-if="props.column" class="group flex items-center justify-between">
		<div class="flex items-center">
			<div class="rounded text-base">{{ props.column }}</div>
		</div>
		<div class="flex select-none items-center justify-end">
			<!-- show sort options only if column is from doc.columns -->
			<div
				v-if="queryColumn"
				@click.prevent.stop="orderByColumn"
				class="ml-4 cursor-pointer py-1 text-gray-500 hover:text-gray-800"
			>
				<FeatherIcon
					v-if="queryColumn.order_by == 'asc'"
					name="arrow-up"
					class="mx-1 h-3 w-3"
				/>
				<FeatherIcon
					v-else-if="queryColumn.order_by == 'desc'"
					name="arrow-down"
					class="mx-1 h-3 w-3"
				/>
				<FeatherIcon v-else name="code" class="mx-1 h-3 w-3 rotate-90" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { inject, computed } from 'vue'

const query = inject('query')
const props = defineProps({
	column: {
		type: String,
		required: true,
	},
})

const queryColumn = computed(() => query.columns.data.find((c) => c.label == props.column))
const orderByColumn = () => {
	if (queryColumn.value.order_by == 'asc') {
		queryColumn.value.order_by = 'desc'
	} else if (queryColumn.value.order_by == 'desc') {
		queryColumn.value.order_by = null
	} else {
		queryColumn.value.order_by = 'asc'
	}
	query.updateColumn.submit({ column: queryColumn.value })
}
</script>
