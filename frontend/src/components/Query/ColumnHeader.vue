<template>
	<div class="group flex items-center justify-between">
		<div class="flex items-center">
			<span
				v-if="column.aggregation"
				class="my-0 mr-2 flex-1 select-none whitespace-nowrap rounded border border-orange-200 px-1 py-0.5 text-xs text-orange-400/80"
			>
				{{ column.aggregation }}
			</span>
			<div class="rounded pr-4 text-base">{{ column.label }}</div>
		</div>
		<div class="flex select-none items-center justify-end">
			<div
				@click.prevent.stop="orderByColumn"
				class="cursor-pointer rounded border border-transparent py-1 text-gray-500 hover:border-gray-200 hover:bg-gray-100 hover:text-gray-600"
			>
				<FeatherIcon v-if="column.order_by == 'asc'" name="arrow-up" class="mx-1 h-3 w-3" />
				<FeatherIcon
					v-else-if="column.order_by == 'desc'"
					name="arrow-down"
					class="mx-1 h-3 w-3"
				/>
				<FeatherIcon v-else name="code" class="mx-1 h-3 w-3 rotate-90" />
			</div>
		</div>
	</div>
</template>

<script setup>
import { inject } from 'vue'

const query = inject('query')
const props = {
	column: {
		type: Object,
		required: true,
	},
}

const orderByColumn = () => {
	props.column.order_by = !props.column.order_by
		? 'asc'
		: props.column.order_by == 'asc'
		? 'desc'
		: null
	query.updateColumn({ column: props.column })
}
</script>
