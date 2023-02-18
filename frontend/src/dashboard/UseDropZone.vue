<script setup>
import { onMounted, onUnmounted, reactive, ref, watchEffect } from 'vue'

const props = defineProps({
	onDrop: { type: Function },
})
const state = reactive({
	isDragging: false,
	ghostElement: { x: 0, y: 0 },
	minLeft: 0,
	maxLeft: 0,
	minTop: 0,
	maxTop: 0,
})

const WIDTH = 128
const HEIGHT = 48

function updateBoundary() {
	const rect = dropZone.value.getBoundingClientRect()
	state.minLeft = rect.left + WIDTH / 2
	state.minTop = rect.top + HEIGHT / 2
	state.maxLeft = rect.right - WIDTH / 2
	state.maxTop = rect.bottom - HEIGHT / 2
}

function updateGhostElement(event) {
	if (!state.isDragging) return

	let x = event.clientX
	let y = event.clientY

	if (x < state.minLeft) x = 0
	else if (x > state.maxLeft) x = state.maxLeft - state.minLeft
	else x = x - WIDTH / 2 - (state.minLeft - WIDTH / 2)

	if (y < state.minTop) y = 0
	else if (y > state.maxTop) y = state.maxTop - state.minTop
	else y = y - HEIGHT / 2 - (state.minTop - HEIGHT / 2)

	state.ghostElement.x = x
	state.ghostElement.y = y
}

const dropZone = ref(null)
const dragEnter = async (event) => {
	updateBoundary()
	updateGhostElement(event)
	state.isDragging = true
}

const dragend = () => (state.isDragging = false)
onMounted(() => {
	updateBoundary()
	window.addEventListener('dragover', updateGhostElement)
	window.addEventListener('dragend', dragend)
	resetPosition()
})
onUnmounted(() => {
	window.removeEventListener('dragover', updateGhostElement)
	window.removeEventListener('dragend', dragend)
})

const drop = (event) => {
	state.isDragging = false
	// consider rect scroll
	const x = event.clientX - (state.minLeft - WIDTH / 2)
	const y = event.clientY - (state.minTop - HEIGHT / 2)
	props.onDrop && props.onDrop(event, { x, y })
}

watchEffect(() => !state.isDragging && resetPosition())
function resetPosition() {
	state.ghostElement.x = state.maxLeft - state.minLeft
	state.ghostElement.y = 0
}
</script>

<template>
	<div
		ref="dropZone"
		@dragenter.prevent="dragEnter"
		@dragover.prevent="() => {}"
		@drop.prevent="drop"
	>
		<div
			class="absolute min-h-[48px] min-w-[128px] rounded-md bg-gray-200/60 transition-all duration-75 ease-out"
			:style="{
				opacity: state.isDragging ? 1 : 0,
				transform: `translate(${state.ghostElement.x}px, ${state.ghostElement.y}px)`,
			}"
		>
			<slot name="ghostElement"> </slot>
		</div>
	</div>
</template>
