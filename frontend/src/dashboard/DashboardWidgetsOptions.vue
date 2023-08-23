<script setup>
import {
	LineChart,
	DollarSign,
	BarChart3,
	PieChart,
	Table,
	BatteryMedium,
	TextCursorInput,
	AlignLeft,
	TrendingUp,
} from 'lucide-vue-next'
import ComboChartIcon from '@/components/Icons/ComboChartIcon.vue'
import widgets from '@/widgets/widgets'
import { inject } from 'vue'
import { ScatterChart } from 'lucide-vue-next'
import { ListFilter } from 'lucide-vue-next'

const dashboard = inject('dashboard')
const emit = defineEmits(['dragChange'])
function onDragStart(widget) {
	emit('dragChange', widget)
	dashboard.draggingWidget = widget
}

const icons = {
	Line: LineChart,
	Number: DollarSign,
	Bar: BarChart3,
	Pie: PieChart,
	Table: Table,
	Progress: BatteryMedium,
	Filter: TextCursorInput,
	Text: AlignLeft,
	Scatter: ScatterChart,
	Funnel: ListFilter,
	Trend: TrendingUp,
	'Mixed Axis': ComboChartIcon,
}
</script>
<template>
	<div class="grid grid-cols-3 gap-3">
		<template v-for="widget in widgets.list" :key="widget.type">
			<div
				:draggable="true"
				class="cursor-grab rounded border border-gray-100 bg-gray-50 pb-2 pt-1 text-center"
				@dragend="emit('dragChange', false)"
				@dragstart="onDragStart(widget)"
			>
				<div class="flex w-full items-center justify-center p-2 text-center">
					<component :is="icons[widget.type]" class="h-6 w-6" :stroke-width="1" />
				</div>
				<span>{{ widget.type }}</span>
			</div>
		</template>
	</div>
</template>
