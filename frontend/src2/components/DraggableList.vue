<script setup>
import { GripVertical, X } from 'lucide-vue-next'
import Draggable from 'vuedraggable'

const emit = defineEmits(['sort'])
const items = defineModel('items')
const props = defineProps({
	items: { type: Array, required: true },
	group: { type: String, required: true },
	itemKey: { type: String, default: 'value' },
	emptyText: { type: String, default: 'No items' },
	showEmptyState: { type: Boolean, default: true },
	showHandle: { type: Boolean, default: true },
})

function onChange(e) {
	if (e.moved) {
		emit('sort', e.moved.oldIndex, e.moved.newIndex)
		items.value.splice(e.moved.newIndex, 0, items.value.splice(e.moved.oldIndex, 1)[0])
	}
	if (e.added) {
		items.value.splice(e.added.newIndex, 0, e.added.element)
	}
	if (e.removed) {
		items.value.splice(e.removed.oldIndex, 1)
	}
}
</script>

<template>
	<Draggable
		class="w-full"
		:model-value="items"
		:group="props.group"
		:item-key="itemKey"
		@change="onChange"
	>
		<template #item="{ element: item, index: idx }">
			<div class="mb-2 flex items-center gap-1 last:mb-0">
				<GripVertical
					v-if="props.showHandle"
					class="h-4 w-4 flex-shrink-0 cursor-grab text-gray-500"
				/>
				<div class="flex flex-1 flex-col justify-center overflow-hidden">
					<slot name="item" :item="item" :index="idx">
						<div
							class="group form-input flex h-7 flex-1 cursor-pointer items-center justify-between px-2"
						>
							<div class="flex items-center space-x-2">
								<div>{{ typeof item === 'object' ? item[itemKey] : item }}</div>
							</div>
							<div class="flex items-center space-x-2">
								<X
									@click.prevent.stop="items.splice(idx, 1)"
									class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
								/>
							</div>
						</div>
					</slot>
				</div>
				<slot name="item-suffix" :item="item" :index="idx" />
			</div>
		</template>
	</Draggable>
	<template v-if="showEmptyState && !items?.length">
		<div
			class="flex h-12 flex-col items-center justify-center rounded border border-dashed border-gray-300 py-2"
		>
			<div class="text-xs text-gray-500">{{ props.emptyText }}</div>
		</div>
	</template>
</template>
