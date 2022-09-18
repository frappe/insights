<template>
	<Draggable
		v-model="items"
		group="items"
		item-key="name"
		:animation="150"
		@sort="onSort"
		class="flex flex-wrap"
		:disabled="resizing || disabled"
	>
		<template #item="{ element: item }">
			<div
				class="relative h-fit w-fit p-1"
				:class="{ 'cursor-grab select-none': resizing || !disabled }"
			>
				<slot name="item" v-bind="{ item }"></slot>
				<div
					v-show="!disabled"
					class="resize-handle absolute right-0 bottom-0 z-10 flex cursor-se-resize items-end pr-2 pb-2"
					:data-id="item.name"
				>
					<div class="h-1 w-2 rounded-l-full bg-gray-300"></div>
					<div class="h-3 w-1 rounded-t-full bg-gray-300"></div>
				</div>
			</div>
		</template>
	</Draggable>
</template>

<script setup>
import Draggable from 'vuedraggable'
import { computed, ref, unref, onMounted, watchEffect } from 'vue'
import useResizer from '@/utils/resizer'

const emit = defineEmits(['sort', 'resize'])
const props = defineProps({
	items: {
		type: Array,
		required: true,
		validator: (value) => {
			return value.every((item) => {
				return item.hasOwnProperty('name')
			})
		},
	},
	enabled: {
		type: Boolean,
		default: true,
	},
})

const items = ref(unref(props.items))
watchEffect(() => {
	items.value = unref(props.items)
})

const disabled = computed(() => !props.enabled)
const resizing = ref(false)

onMounted(() => {
	const handles = document.querySelectorAll('.resize-handle')
	handles.forEach((handle) => {
		useResizer({
			disabled,
			handle,
			target: handle.previousElementSibling,
			start: () => (resizing.value = true),
			stop: () => (resizing.value = false),
			resize(width, height) {
				emit('resize', {
					width: width,
					height: height,
					name: handle.getAttribute('data-id'),
				})
			},
		})
	})
})

const onSort = (e) => {
	if (e.oldIndex != e.newIndex) {
		emit('sort', e)
	}
}
</script>
