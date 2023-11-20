import { ref, unref, reactive, computed } from 'vue'

export default function useResizer({
	handle,
	target,
	direction,
	limits,
	inverse,
	disabled,
	start,
	stop,
	onResize,
}) {
	const isDragging = ref(false)
	const startX = ref(0)
	const startY = ref(0)

	const state = reactive({
		startWidth: 0,
		startHeight: 0,
		newWidth: 0,
		newHeight: 0,
	})

	const disableDragging = computed(() => unref(disabled))

	const $target = unref(target)

	function onMouseDown(e) {
		if (disableDragging.value) {
			return
		}

		// e.preventDefault()

		start && start()
		isDragging.value = true
		startX.value = e.clientX
		startY.value = e.clientY
		state.startWidth = parseInt(document.defaultView.getComputedStyle($target).width, 10)
		state.startHeight = parseInt(document.defaultView.getComputedStyle($target).height, 10)

		document.addEventListener('mousemove', onMouseMove)
		document.addEventListener('mouseup', onMouseUp)
	}

	function onMouseMove(e) {
		if (isDragging.value) {
			const dx = e.clientX - startX.value
			const dy = e.clientY - startY.value

			if (!direction || direction == 'x') {
				state.newWidth = inverse ? state.startWidth - dx : state.startWidth + dx
				if (limits) {
					if (state.newWidth < limits.minWidth) {
						state.newWidth = limits.minWidth
					} else if (state.newWidth > limits.maxWidth) {
						state.newWidth = limits.maxWidth
					}
				}
				$target.style.width = state.newWidth + 'px'
			}

			if (!direction || direction == 'y') {
				state.newHeight = inverse ? state.startHeight - dy : state.startHeight + dy
				if (limits) {
					if (state.newHeight < limits.minHeight) {
						state.newHeight = limits.minHeight
					} else if (state.newHeight > limits.maxHeight) {
						state.newHeight = limits.maxHeight
					}
				}
				$target.style.height = `${state.newHeight}px`
			}
		}
	}

	function onMouseUp() {
		isDragging.value = false
		document.removeEventListener('mousemove', onMouseMove)
		document.removeEventListener('mouseup', onMouseUp)

		stop && stop()
		onResize && onResize(state.newWidth, state.newHeight)
	}

	unref(handle).addEventListener('mousedown', onMouseDown)
}
