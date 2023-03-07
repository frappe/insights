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
} from 'lucide-vue-next'
import widgets from '@/widgets/widgets'
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
}
</script>
<template>
	<div class="grid grid-cols-3 gap-3">
		<template v-for="widget in widgets.list" :key="widget.type">
			<div
				class="cursor-grab rounded-md border border-gray-100 bg-gray-50 pt-1 pb-2 text-center text-gray-600"
			>
				<div
					:draggable="true"
					class="flex w-full items-center justify-center p-2 text-center"
					@dragend="emit('dragChange', false)"
					@dragstart="onDragStart(widget)"
				>
					<component :is="icons[widget.type]" class="h-6 w-6" :stroke-width="1" />
				</div>
				<span>{{ widget.type }}</span>
			</div>
		</template>
	</div>
</template>
