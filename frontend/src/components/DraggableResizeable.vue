<template>
	<Draggable
		v-model="items"
		group="items"
		item-key="name"
		:animation="150"
		@sort="onSort"
		class="flex flex-wrap"
		:disabled="dragDisabled"
	>
		<template #item="{ element: item }">
			<div class="relative flex items-start p-1">
				<slot name="item" v-bind="{ item }"></slot>
				<div
					v-show="props.enabled"
					ref="resizeHandle"
					class="absolute right-0 bottom-0 z-10 flex cursor-se-resize items-end pr-2 pb-2"
					:data-id="item.name"
				>
					<div class="h-1 w-4 rounded-l-full bg-gray-200"></div>
					<div class="h-5 w-1 rounded-t-full bg-gray-200"></div>
				</div>
			</div>
		</template>
	</Draggable>
</template>

<script setup>
import Draggable from 'vuedraggable'
import { computed, ref, unref, onMounted } from 'vue'
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

const resizing = ref(false)
const dragDisabled = computed(() => resizing.value || !props.enabled)

const resizeHandle = ref(null)

onMounted(() => {
	useResizer({
		disabled: !props.enabled,
		handle: resizeHandle,
		target: resizeHandle.value.previousElementSibling,
		start: () => (resizing.value = true),
		stop: () => (resizing.value = false),
		resize(width, height) {
			emit('resize', {
				width: width,
				height: height,
				name: resizeHandle.value.getAttribute('data-id'),
			})
		},
	})
})

const onSort = (e) => {
	if (e.oldIndex != e.newIndex) {
		emit('sort', e)
	}
}
</script>
