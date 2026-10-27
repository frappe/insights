import { useEventListener } from '@vueuse/core'

type Target = {
	tagName?: string
	isContentEditable?: boolean
	closest?: (selector: string) => unknown
} | null

// A text box has its own undo, and a dialog covers the builder it would undo
function keepsItsKeys(target: Target) {
	return Boolean(
		target?.isContentEditable ||
			['INPUT', 'TEXTAREA', 'SELECT'].includes(target?.tagName || '') ||
			target?.closest?.('[role="dialog"]'),
	)
}

/** What a key press asks of a builder's history. */
export function undoKeyAction(event: KeyboardEvent): 'undo' | 'redo' | undefined {
	if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'z') return
	if (keepsItsKeys(event.target as Target)) return
	return event.shiftKey ? 'redo' : 'undo'
}

/** ⌘Z or Ctrl+Z undoes, with Shift it redoes, while the builder is mounted. */
export function useUndoKeys(history: { undo: () => void; redo: () => void }) {
	useEventListener(window, 'keydown', (event: KeyboardEvent) => {
		const action = undoKeyAction(event)
		if (!action) return
		event.preventDefault()
		history[action]()
	})
}
