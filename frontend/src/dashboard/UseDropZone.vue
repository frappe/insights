<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watchEffect } from 'vue'

const props = defineProps({
	onDrop: { type: Function },
	showCollision: { type: Boolean, default: false },
	colliderClass: { type: String, default: '.collider' },
	ghostWidth: { type: Number, default: 128 },
	ghostHeight: { type: Number, default: 48 },
})
const state = reactive({
	isDragging: false,
	collides: false,
	ghost: { x: 0, y: 0 },
	minLeft: 0,
	maxLeft: 0,
	minTop: 0,
	maxTop: 0,
	ghostWidth: computed(() => props.ghostWidth),
	ghostHeight: computed(() => props.ghostHeight),
})

function updateBoundary() {
	const rect = dropZone.value.getBoundingClientRect()
	state.minLeft = rect.left + state.ghostWidth / 2
	state.minTop = rect.top + state.ghostHeight / 2
	state.maxLeft = rect.right - state.ghostWidth / 2
	state.maxTop = rect.bottom - state.ghostHeight / 2
}

function updateGhostElement(event) {
	if (!state.isDragging) return

	let x = event.clientX
	let y = event.clientY

	if (x < state.minLeft) x = 0
	else if (x > state.maxLeft) x = state.maxLeft - state.minLeft
	else x = x - state.ghostWidth / 2 - (state.minLeft - state.ghostWidth / 2)

	if (y < state.minTop) y = 0
	else if (y > state.maxTop) y = state.maxTop - state.minTop
	else y = y - state.ghostHeight / 2 - (state.minTop - state.ghostHeight / 2)

	state.ghost.x = x
	state.ghost.y = y

	if (props.showCollision) checkCollision()
}

const checkCollision = function () {
	requestAnimationFrame(() => {
		const ghostElement = document.querySelector('.ghost-element')
		if (!ghostElement) return
		const ghostRect = ghostElement.getBoundingClientRect()
		// check if the ghost element intersects with any element with collider class
		const intersects = Array.from(document.querySelectorAll(props.colliderClass)).some((el) => {
			const rect = el.getBoundingClientRect()
			return (
				ghostRect.left < rect.right &&
				ghostRect.right > rect.left &&
				ghostRect.top < rect.bottom &&
				ghostRect.bottom > rect.top
			)
		})
		state.collides = intersects
	})
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
	const x = event.clientX - state.minLeft
	const y = event.clientY - state.minTop
	const collides = state.collides
	props.onDrop && props.onDrop({ x, y, collides })
}

watchEffect(() => !state.isDragging && resetPosition())
function resetPosition() {
	state.ghost.x = state.maxLeft - state.minLeft
	state.ghost.y = 0
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
			class="ghost-element absolute rounded bg-gray-200/60 transition-all duration-75 ease-out"
			:class="[props.showCollision && state.collides ? 'bg-red-200/60' : '']"
			:style="{
				opacity: state.isDragging ? 1 : 0,
				transform: `translate(${state.ghost.x}px, ${state.ghost.y}px)`,
				width: `${state.ghostWidth}px`,
				height: `${state.ghostHeight}px`,
			}"
		></div>
	</div>
</template>
