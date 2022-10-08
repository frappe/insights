<template>
	<div class="h-full w-full rounded-md bg-gray-50">
		<div
			v-if="show"
			class="group relative flex h-full w-full flex-col overflow-hidden rounded-md border border-gray-300 bg-white p-3"
		>
			<div
				v-if="!dashboard.editingLayout"
				class="invisible absolute top-2 right-2 z-10 flex h-5 items-center group-hover:visible"
			>
				<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
					<FeatherIcon
						name="external-link"
						class="h-3.5 w-3.5"
						@mousedown.prevent.stop=""
						@click.prevent.stop="$emit('edit', props.queryID)"
					/>
				</div>
				<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
					<FeatherIcon
						name="x"
						class="h-4 w-4"
						@mousedown.prevent.stop=""
						@click.prevent.stop="$emit('remove', props.chartID)"
					/>
				</div>
			</div>
			<div class="h-full">
				<component
					v-if="chart.component && chart.componentProps"
					:is="chart.component"
					v-bind="chart.componentProps"
				></component>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, inject } from 'vue'
import { useQueryChart } from '@/utils/charts'

const emit = defineEmits(['edit', 'remove'])

const dashboard = inject('dashboard')
const props = defineProps({
	chartID: {
		type: String,
		required: true,
	},
	queryID: {
		type: String,
		required: true,
	},
})

const show = computed(() => {
	return chart.type && chart.component && chart.componentProps
})

const chart = useQueryChart({
	chartID: props.chartID,
	queryID: props.queryID,
})
</script>
