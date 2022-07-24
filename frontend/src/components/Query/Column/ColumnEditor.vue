<template>
	<div class="mb-4 flex h-7 items-center">
		<Button icon="chevron-left" class="mr-2" @click="$emit('close')"> </Button>
		<div class="text-lg font-medium">Edit {{ props.column.label }}</div>
	</div>
	<div class="flex flex-col space-y-3">
		<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
			<div
				v-for="tab in [columnType, 'Format']"
				class="flex h-full flex-1 items-center justify-center rounded-md"
				:class="{ 'border bg-white font-normal shadow-sm': currentTab == tab }"
				@click.prevent.stop="currentTab = tab"
			>
				{{ tab }}
			</div>
		</div>
		<MetricPicker
			v-if="currentTab == 'Metric'"
			:column="props.column"
			@column-select="editColumn"
			@close="$emit('close')"
		/>
		<DimensionPicker
			v-if="currentTab == 'Dimension'"
			:column="props.column"
			@column-select="editColumn"
			@close="$emit('close')"
		/>
		<ColumnExpressionPicker
			v-if="currentTab == 'Expression'"
			:column="props.column"
			@column-select="editColumn"
			@close="$emit('close')"
		/>
		<ColumnFormatter v-if="currentTab == 'Format'" :column="props.column" @save="editColumn" />
	</div>
</template>

<script setup>
import MetricPicker from '@/components/Query/Column/MetricPicker.vue'
import DimensionPicker from '@/components/Query/Column/DimensionPicker.vue'
import ColumnFormatter from '@/components/Query/Column/ColumnFormatter.vue'
import ColumnExpressionPicker from '@/components/Query/Column/ColumnExpressionPicker.vue'

import { inject, ref } from 'vue'

const emit = defineEmits(['close'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
		required: true,
	},
})
const query = inject('query')
const columnType = ref(
	props.column.is_expression
		? 'Expression'
		: props.column.aggregation && props.column.aggregation === 'Group By'
		? 'Dimension'
		: 'Metric'
)
const currentTab = ref(columnType.value)

const editColumn = (column) => {
	query.updateColumn.submit({ column })
	emit('close')
}
</script>
