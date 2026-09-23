// The line under a drill level: where the server cut it.

import { __ } from '../../translation'

/**
 * What the dialog says beneath the level being read.
 *
 * Only a breakdown has this to declare, and only when it was cut: a level that
 * came back whole says nothing the picture does not. Which few came back is the
 * level's own reading — a ranked breakdown is cut to the biggest groups and an
 * ordered one to its most recent stretch, so one says "top" and the other says
 * "latest".
 *
 * A rows level is silent here because it is not cut: it is paged, and the pane
 * it is drawn in states the page and the total it is a page of. Two lines
 * saying the same number, one of them stale as soon as the reader turned a
 * page, is what that would be instead.
 */
export function levelBound(level: {
	breakdown: boolean
	ordered: boolean
	shown: number
	total?: number
}): string {
	if (!level.breakdown) return ''
	if (!level.total || level.total <= level.shown) return ''

	const shown = level.shown.toLocaleString()
	const total = level.total.toLocaleString()
	return level.ordered
		? __('latest {0} of {1} periods', shown, total)
		: __('top {0} of {1} groups', shown, total)
}
