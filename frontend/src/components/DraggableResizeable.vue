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
	enabled: {
		type: Boolean,
		default: true,
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
		new DraggableResizeable(target, parent, {
			snapToGrid: true,
			onMove: (x, y) => emit('move', { x, y }),
			onResize: (width, height) => emit('resize', { width, height }),
		})
	})
})

class DraggableResizeable {
	constructor(element, parent, { minWidth, minHeight, snapToGrid, onMove, onResize }) {
		this.element = element
		this.parent = parent
		this.onMove = onMove
		this.onResize = onResize
		this.minWidth = minWidth || 50
		this.minHeight = minHeight || 50
		this.snapToGrid = snapToGrid || false
		this.init()
	}

	init() {
		this.boundary = this.parent.getBoundingClientRect().toJSON()

		if (this.snapToGrid) {
			this.columnWidth = 5
			this.rowHeight = 5
		}

		this.attachResizers()
		this.attachListeners()
	}

	attachResizers() {
		this.createResizerElement()
	}

	attachListeners() {
		this.element.addEventListener('mousedown', this.onMouseDown.bind(this))
	}

	removeListeners() {
		this.element.removeEventListener('mousedown', this.onMouseDown)
	}

	onMouseDown(e) {
		if (!props.enabled) {
			this.removeListeners()
			return
		}
		this.element.classList.add('cursor-grabbing', 'z-10')
		if (e.target.classList.contains('cursor-se-resize')) {
			this.isResizing = true
			this.isDragging = false
		} else {
			this.isDragging = true
			this.isResizing = false
		}

		this.dragStartX = e.clientX
		this.dragStartY = e.clientY

		window.addEventListener('mousemove', this.onMouseMove.bind(this))
		window.addEventListener('mouseup', this.onMouseUp.bind(this))
	}

	onMouseUp() {
		if (!props.enabled) {
			this.removeListeners()
			return
		}
		const rect = this.element.getBoundingClientRect()
		const relativeToParent = this.convertToRelative(rect)

		this.isResizing && this.onResize && this.onResize(rect.width, rect.height)
		this.isDragging &&
			this.onMove &&
			this.onMove(relativeToParent.left, this.parent.scrollTop + relativeToParent.top)

		this.element.classList.remove('cursor-grabbing', 'z-10')
		this.isDragging = false
		this.isResizing = false

		this.removeListeners()
	}

	removeListeners() {
		window.removeEventListener('mousemove', this.onMouseMove)
		window.removeEventListener('mouseup', this.onMouseUp)
	}

	convertToRelative(rect) {
		return {
			width: rect.width,
			height: rect.height,
			top: rect.top - this.boundary.top,
			left: rect.left - this.boundary.left,
			right: rect.right - this.boundary.right,
			bottom: rect.bottom - this.boundary.bottom,
		}
	}

	onMouseMove(e) {
		if (!props.enabled) {
			return
		}

		if (!this.isDragging && !this.isResizing) {
			return
		}

		let dx = e.clientX - this.dragStartX
		let dy = e.clientY - this.dragStartY

		if (this.snapToGrid) {
			dx = Math.round(dx / this.columnWidth) * this.columnWidth
			dy = Math.round(dy / this.rowHeight) * this.rowHeight
		}

		if (dx === 0 && dy === 0) {
			return
		}

		if (this.isDragging) {
			const rect = this.convertToRelative(this.element.getBoundingClientRect())
			this.element.style.left = `${rect.left + dx}px`
			this.element.style.top = `${this.parent.scrollTop + rect.top + dy}px`
			this.checkBoundaryAndSnap()
		}

		if (this.isResizing) {
			const rect = this.element.getBoundingClientRect()
			let newWidth = rect.width + dx
			let newHeight = rect.height + dy

			if (this.snapToGrid) {
				newWidth = Math.round(newWidth / this.columnWidth) * this.columnWidth
				newHeight = Math.round(newHeight / this.rowHeight) * this.rowHeight
			}

			this.element.style.width = `${newWidth}px`
			this.element.style.height = `${newHeight}px`
			this.checkBoundaryAndResize(newWidth, newHeight)
		}
		this.dragStartX = e.clientX
		this.dragStartY = e.clientY
	}

	checkBoundaryAndSnap() {
		const newRect = this.element.getBoundingClientRect()
		if (newRect.left < this.boundary.left) {
			this.element.style.left = '0px'
		} else if (newRect.right > this.boundary.right) {
			this.element.style.left = `${
				this.boundary.right - this.boundary.left - newRect.width
			}px`
		}
		if (this.parent.scrollTop + newRect.top < this.boundary.top) {
			this.element.style.top = '0px'
		}
		// else if (newRect.bottom > this.boundary.bottom) {
		// 	this.element.style.top = `${
		// 		this.boundary.bottom - this.boundary.top - newRect.height
		// 	}px`
		// }
	}

	checkBoundaryAndResize(newWidth, newHeight) {
		newWidth = Math.max(newWidth, this.minWidth)
		newHeight = Math.max(newHeight, this.minHeight)
		newWidth = Math.min(newWidth, this.boundary.width)

		if (newHeight > this.boundary.height) {
			// scroll parent container to bottom
			this.parent.scrollTop = this.parent.scrollHeight
		}
		this.element.style.width = `${newWidth}px`
		this.element.style.height = `${newHeight}px`
	}

	createResizerElement() {
		this.resizer = document.createElement('div')
		this.resizer.classList.add(
			'absolute',
			'bottom-0',
			'right-0',
			'h-5',
			'w-5',
			'cursor-se-resize'
		)
		this.element.appendChild(this.resizer)
	}
}
</script>
