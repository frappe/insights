<script setup>
import widgets from './widgets/widgets'
const emit = defineEmits(['dragChange'])
</script>
<template>
	<div class="grid grid-cols-3 gap-2">
		<template v-for="widget in widgets.list" :key="widget.type">
			<div class="cursor-grab text-center text-sm text-gray-600">
				<div
					:draggable="true"
					class="mb-1 flex h-16 w-full items-center justify-center rounded-md border bg-gray-50 p-6 text-center"
					@dragend="emit('dragChange', false)"
					@dragstart="
						(event) => {
							emit('dragChange', true)
							event.dataTransfer.setData('text/plain', widget.type)
						}
					"
				>
					<FeatherIcon :name="widget.icon" class="h-6 w-6 text-gray-400" />
				</div>
				<span>{{ widget.type }}</span>
			</div>
		</template>
	</div>
</template>
