type DragOptions = {
	/** Held for the whole drag, so a hovered element cannot take the cursor. */
	cursor?: string
	// eslint-disable-next-line no-unused-vars
	onMove: (event: MouseEvent) => void
}

let overlay: HTMLDivElement | null = null

function holdCursor(cursor: string) {
	overlay = document.createElement('div')
	overlay.style.position = 'fixed'
	overlay.style.inset = '0'
	overlay.style.zIndex = '2147483647'
	overlay.style.cursor = cursor
	document.body.appendChild(overlay)
}

function releaseCursor() {
	overlay?.remove()
	overlay = null
}

/**
 * Runs a mouse drag until the button is released or Escape is pressed.
 *
 * A panel field is nudged far more often than it is typed, so its label is a
 * handle. Ported from Builder, which drags the side labels of its box controls.
 */
export function startDrag({ cursor, onMove }: DragOptions) {
	if (cursor) holdCursor(cursor)

	function move(event: MouseEvent) {
		onMove(event)
		event.preventDefault()
	}

	function stop() {
		document.removeEventListener('mousemove', move)
		document.removeEventListener('mouseup', stop)
		document.removeEventListener('keydown', cancel)
		releaseCursor()
	}

	function cancel(event: KeyboardEvent) {
		if (event.key !== 'Escape') return
		event.preventDefault()
		stop()
	}

	document.addEventListener('mousemove', move)
	document.addEventListener('mouseup', stop)
	document.addEventListener('keydown', cancel)
}
