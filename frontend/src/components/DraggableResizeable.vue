<template>
	<slot />
</template>

<script setup>
import { nextTick, onMounted } from 'vue'

const props = defineProps({
	parentID: {
		type: String,
		required: true,
	},
	targetID: {
		type: String,
		required: true,
	},
	maintainAspectRatio: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['move', 'resize'])

onMounted(() => {
	nextTick(() => {
		const parent = document.getElementById(props.parentID)
		const target = document.getElementById(props.targetID)
		if (!parent || !target) {
			return
		}
		new DraggableResizeable({
			element: target,
			parent: parent,
			onMove: (x, y) => {
				emit('move', { id: props.targetID, x, y })
			},
			onResize: (width, height) => {
				emit('resize', { id: props.targetID, width, height })
			},
		})
	})
})

class DraggableResizeable {
	constructor({ element, parent, onMove, onResize }) {
		this.element = element
		this.parent = parent
		this.onMove = onMove
		this.onResize = onResize
		this.init()
	}

	init() {
		this.currentX = parseFloat(this.element.getAttribute('data-x')) || 0
		this.currentY = parseFloat(this.element.getAttribute('data-y')) || 0

		this.element.style.transform = `translate(0px, 0px)`
		this.actualPosition = this.element.getBoundingClientRect().toJSON()
		this.element.style.transform = `translate(${this.currentX}px, ${this.currentY}px)`
		this.element.classList.add('cursor-grab')

		this.boundary = this.parent.getBoundingClientRect().toJSON()

		this.attachResizers()
		this.attachListeners()
	}

	attachResizers() {
		this.element.classList.add('relative', 'z-10')
		this.element.appendChild(this.createResizerElement())
	}

	attachListeners() {
		this.element.addEventListener('mousedown', this.onMouseDown.bind(this))
	}

	removeListeners() {
		this.element.removeEventListener('mousedown', this.onMouseDown)
	}

	onMouseDown(e) {
		this.element.classList.add('cursor-grabbing', 'opacity-50', 'z-10')
		if (e.target.classList.contains('cursor-se-resize')) {
			this.isResizing = true
			this.isDragging = false
		} else {
			this.isDragging = true
			this.isResizing = false
		}

		this.startX = e.clientX
		this.startY = e.clientY
		this.prevX = e.clientX
		this.prevY = e.clientY
		window.addEventListener('mousemove', this.onMouseMove.bind(this))
		window.addEventListener('mouseup', this.onMouseUp.bind(this))
	}

	onMouseUp(e) {
		this.currentX = this.lastX
		this.currentY = this.lastY

		this.isDragging && this.onMove && this.onMove(this.currentX, this.currentY)
		this.isResizing && this.onResize && this.onResize(this.currentWidth, this.currentHeight)

		this.element.classList.remove('cursor-grabbing', 'opacity-50', 'z-10')
		this.isDragging = false
		this.isResizing = false

		window.removeEventListener('mousemove', this.onMouseMove)
		window.removeEventListener('mouseup', this.onMouseUp)
	}

	onMouseMove(e) {
		if (this.isDragging) {
			const dx = e.clientX - this.startX
			const dy = e.clientY - this.startY

			let moveX = this.currentX + dx
			let moveY = this.currentY + dy

			this.element.style.transform = `translate(${moveX}px, ${moveY}px)`
			let [x, y] = this.checkBoundary(moveX, moveY)
			this.lastX = x
			this.lastY = y
			return
		}

		if (this.isResizing) {
			const dx = e.clientX - this.prevX
			const dy = e.clientY - this.prevY

			const rect = this.element.getBoundingClientRect()

			let newWidth = rect.width + dx
			let newHeight = rect.height + dy

			if (newWidth < 300) {
				newWidth = 300
			}
			if (newHeight < 300) {
				newHeight = 300
			}
			if (newWidth > this.boundary.width) {
				newWidth = this.boundary.width
			}
			if (newHeight > this.boundary.height) {
				// scroll parent container to bottom
				this.parent.scrollTop = this.parent.scrollHeight
			}

			this.element.style.width = `${newWidth}px`
			this.element.style.height = props.maintainAspectRatio
				? `${(newWidth / this.actualPosition.width) * this.actualPosition.height}px`
				: `${newHeight}px`

			this.prevX = e.clientX
			this.prevY = e.clientY
			this.currentWidth = newWidth
			this.currentHeight = newHeight
			return
		}
	}

	checkBoundary(moveX, moveY) {
		const elementBoundary = this.element.getBoundingClientRect()

		if (elementBoundary.left < this.boundary.left) {
			moveX = this.boundary.left - this.actualPosition.left
		} else if (elementBoundary.right > this.boundary.right) {
			moveX = this.boundary.right - this.actualPosition.left - elementBoundary.width
		}

		if (elementBoundary.top < this.boundary.top) {
			moveY = this.boundary.top - this.actualPosition.top
		} else if (elementBoundary.bottom > this.boundary.bottom) {
			moveY = this.boundary.bottom - this.actualPosition.top - elementBoundary.height
		}

		moveX = parseInt(moveX)
		moveY = parseInt(moveY)
		this.element.style.transform = `translate(${moveX}px, ${moveY}px)`

		return [moveX, moveY]
	}

	createResizerElement() {
		const resizer = document.createElement('div')
		resizer.classList.add('absolute', 'top-0', 'left-0', 'z-0', 'h-full', 'w-full')
		const resizerInner = document.createElement('div')
		resizerInner.classList.add('relative', 'h-full', 'w-full')

		const resizerBottom = document.createElement('div')
		this.resizerBottom = resizerBottom
		resizerBottom.classList.add(
			'h-5',
			'w-5',
			'absolute',
			'-bottom-[4px]',
			'-right-[4px]',
			'cursor-se-resize'
		)
		resizerInner.appendChild(resizerBottom)

		resizer.appendChild(resizerInner)
		return resizer
	}
}
</script>
