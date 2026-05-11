import { useMagicKeys } from '@vueuse/core'
import { onUnmounted, watch } from 'vue'

const isMac = navigator.platform.toUpperCase().includes('MAC')

export function formatShortcut(shortcut: string): string {
	return shortcut
		.split('+')
		.map((part) => {
			switch (part.toLowerCase()) {
				case 'meta':
					return isMac ? '⌘' : 'Ctrl'
				case 'ctrl':
					return 'Ctrl'
				case 'shift':
					return isMac ? '⇧' : 'Shift'
				case 'alt':
					return isMac ? '⌥' : 'Alt'
				default:
					return part.toUpperCase()
			}
		})
		.join(isMac ? '' : '+')
}

function parseShortcut(shortcut: string) {
	const parts = shortcut.toLowerCase().split('+')
	return {
		meta: parts.includes('meta'),
		ctrl: parts.includes('ctrl'),
		shift: parts.includes('shift'),
		alt: parts.includes('alt'),
		key: parts[parts.length - 1],
	}
}

export function useShortcut(shortcut: string, callback: () => void) {
	const parsed = parseShortcut(shortcut)

	const keys = useMagicKeys({
		passive: false,
		onEventFired(e) {
			if (
				e.type === 'keydown' &&
				e.key.toLowerCase() === parsed.key &&
				e.metaKey === parsed.meta &&
				e.ctrlKey === parsed.ctrl &&
				e.shiftKey === parsed.shift &&
				e.altKey === parsed.alt
			) {
				e.preventDefault()
			}
		},
	})

	const key = keys[shortcut]
	const stop = watch(key, (value) => {
		if (value) {
			callback()
		}
	})
	onUnmounted(stop)
}
