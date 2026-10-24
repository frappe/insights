import { __ } from '../../translation'

/**
 * Only a breakdown shows it, and only when the server returned fewer groups
 * than exist. The wording follows how the level
 * was limited: a ranked breakdown keeps the biggest groups ("top"), and an
 * ordered one keeps the most recent periods ("latest").
 *
 * A rows level shows nothing here because it is paged, not limited, and the
 * pane already shows the page and the total. A second line would repeat that
 * number and go stale when the reader turns a page.
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
