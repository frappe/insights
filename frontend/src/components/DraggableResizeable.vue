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
			<div class="relative p-1">
				<slot name="item" v-bind="{ item }"></slot>
				<div
					class="resizer absolute right-0 z-10 flex h-6 w-6 -translate-y-4 cursor-se-resize"
					:data-id="item.name"
				></div>
			</div>
		</template>
	</Draggable>
</template>

<script setup>
import Draggable from 'vuedraggable'
import { computed, ref, watch, unref } from 'vue'
import { useMagicKeys } from '@vueuse/core'

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
const SNAP_WIDTH = 5

const keys = useMagicKeys()
const cmd = keys['Meta']
const enableFineMovement = ref(false)
watch(cmd, (pressed) => {
	enableFineMovement.value = pressed
})

document.addEventListener('mousedown', (e) => {
	if (!e.target.classList.contains('resizer') || !props.enabled) return

	e.preventDefault()
	const resizer = e.target
	resizing.value = true

	let startX, startY
	startX = e.clientX
	startY = e.clientY

	window.addEventListener('mousemove', resize)
	window.addEventListener('mouseup', stopResize)

	function resize(e) {
		let dx = e.clientX - startX
		let dy = e.clientY - startY

		if (!enableFineMovement.value) {
			dx = Math.round(dx / SNAP_WIDTH) * SNAP_WIDTH
			dy = Math.round(dy / SNAP_WIDTH) * SNAP_WIDTH
		}

		if (dx === 0 && dy === 0) return

		const target = resizer.previousElementSibling
		const rect = target.getBoundingClientRect()
		let newWidth = rect.width + dx
		let newHeight = rect.height + dy

		if (!enableFineMovement.value) {
			newWidth = Math.round(newWidth / SNAP_WIDTH) * SNAP_WIDTH
			newHeight = Math.round(newHeight / SNAP_WIDTH) * SNAP_WIDTH
		}

		target.style.width = `${newWidth}px`
		target.style.height = `${newHeight}px`

		startX = e.clientX
		startY = e.clientY
	}

	function stopResize() {
		resizing.value = false
		const element = resizer.previousElementSibling
		emit('resize', {
			name: resizer.getAttribute('data-id'),
			width: parseInt(element.style.width.replace('px', '')),
			height: parseInt(element.style.height.replace('px', '')),
		})
		window.removeEventListener('mousemove', resize)
	}
})

const onSort = (e) => {
	if (e.oldIndex != e.newIndex) {
		emit('sort', e)
	}
}
</script>
