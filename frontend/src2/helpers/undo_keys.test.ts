import { describe, expect, it } from 'vitest'
import { undoKeyAction } from './undo_keys'

const on = (tagName: string, isContentEditable = false, inDialog = false) => ({
	tagName,
	isContentEditable,
	closest: (selector: string) => (inDialog && selector.includes('dialog') ? {} : null),
})
const press = (
	keys: { key: string; metaKey?: boolean; ctrlKey?: boolean; shiftKey?: boolean },
	target = on('BODY'),
) => undoKeyAction({ metaKey: false, ctrlKey: false, shiftKey: false, ...keys, target } as any)

describe('the undo shortcut', () => {
	// @feature query.undo-redo
	it('undoes on ⌘Z or Ctrl+Z, and redoes on ⌘⇧Z without undoing first', () => {
		expect(press({ key: 'z', metaKey: true })).toBe('undo')
		expect(press({ key: 'z', ctrlKey: true })).toBe('undo')
		expect(press({ key: 'Z', metaKey: true, shiftKey: true })).toBe('redo')
		expect(press({ key: 'z' })).toBeUndefined()
	})

	// @feature query.undo-redo
	it('leaves a text box its own undo', () => {
		expect(press({ key: 'z', metaKey: true }, on('INPUT'))).toBeUndefined()
		expect(press({ key: 'z', metaKey: true }, on('TEXTAREA'))).toBeUndefined()
		expect(press({ key: 'z', metaKey: true }, on('DIV', true))).toBeUndefined()
	})

	// @feature query.undo-redo
	it('leaves the builder behind an open dialog alone', () => {
		expect(press({ key: 'z', metaKey: true }, on('BUTTON', false, true))).toBeUndefined()
	})
})
