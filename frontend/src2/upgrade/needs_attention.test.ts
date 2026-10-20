import { describe, expect, it } from 'vitest'
import { attentionGroups } from './needs_attention'
import type { UpgradeItem } from './upgrade'

function item(name: string, code: string): UpgradeItem {
	return {
		name,
		code,
		message: name,
		reference_doctype: null,
		reference_name: null,
		user: null,
		action: null,
		workbook: null,
		form_url: null,
		can_fix: false,
	}
}

describe('attentionGroups', () => {
	// @feature upgrade.attention-items
	it('puts data access first and keeps an item whose code has no heading', () => {
		const groups = attentionGroups([
			item('copy', 'W2'),
			item('first chart', 'P10'),
			item('new code', 'Z9'),
			item('alice', 'P17'),
			item('second chart', 'P10'),
		])

		expect(groups.map((group) => [group.code, group.items.map((i) => i.name)])).toEqual([
			['P17', ['alice']],
			['P10', ['first chart', 'second chart']],
			['W2', ['copy']],
			['Z9', ['new code']],
		])
		expect(groups[3].title).toBe('Other changes')
	})
})
