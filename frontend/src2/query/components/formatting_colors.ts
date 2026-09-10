import { type ChartTokens } from 'frappe-ui/charts'

/**
 * Which end of a scale gets the deep color. A scale ranks by lightness, so the
 * only choice it has to offer is which end is heavy. The stored name says that
 * and not a color, so the ramp can be rebranded without turning every saved
 * rule into a lie.
 */
export type ColorScaleDirection = 'ascending' | 'descending'

/**
 * The two names this option carried when the scale ran red to green. Each named
 * the end it treated as the alarming one, which is the end that now goes deep.
 */
const LEGACY_DIRECTIONS: Record<string, ColorScaleDirection> = {
	'Green-Red': 'ascending',
	'Red-Green': 'descending',
}

export function colorScaleDirection(stored: string | undefined): ColorScaleDirection {
	if (stored === 'ascending' || stored === 'descending') return stored
	return LEGACY_DIRECTIONS[stored ?? ''] ?? 'ascending'
}

/** A cell's fill and the ink that sits on it. */
export type CellFill = {
	backgroundColor: string
	color: string
}

/**
 * Below this relative luminance a fill needs white text. The number is
 * frappe-ui's: white and the near-black label ink contrast equally at 0.22.
 */
const DARK_FILL_LUMINANCE = 0.22

function hexLuminance(color: string): number | null {
	const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color.trim())
	if (!match) return null

	const hex =
		match[1].length === 3
			? match[1]
					.split('')
					.map((c) => c + c)
					.join('')
			: match[1]

	const channels = [0, 2, 4].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
	const linear = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4))
	const [r, g, b] = channels.map(linear)
	return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/**
 * The ink for a number printed on `background`. Only hex parses, because every
 * `--chart-*` stop is authored as hex. Anything else keeps the token ink.
 */
function inkOn(background: string, tokens: ChartTokens): string {
	const luminance = hexLuminance(background)
	if (luminance === null) return tokens.insideLabel
	return luminance < DARK_FILL_LUMINANCE ? '#ffffff' : tokens.insideLabel
}

/**
 * A scale, from the bottom of the range to the top. The first slot is empty on
 * purpose: the bottom of a magnitude scale is an absence, so a zero draws
 * nothing rather than drawing the heaviest thing on the page.
 *
 * It reads `tokens.sequential` rather than going through `paletteColors`. That
 * sampler drops the ramp's two palest stops because they vanish against a card
 * — which is what the shallow end of a table scale is supposed to do.
 *
 * One hue and nothing else. Lightness is the only channel a reader orders
 * without a legend, so a scale spends it and leaves hue to say what a cell
 * means. See `statusFill`, which owns the other half of that rule.
 */
export function magnitudeScale(
	tokens: ChartTokens,
	direction: ColorScaleDirection = 'ascending',
): (CellFill | undefined)[] {
	const paleToDeep = tokens.sequential
		.slice()
		.reverse()
		.map((backgroundColor) => ({ backgroundColor, color: inkOn(backgroundColor, tokens) }))

	const scale: (CellFill | undefined)[] = [undefined, ...paleToDeep]
	return direction === 'descending' ? scale.reverse() : scale
}

/**
 * The stop a value lands on. `percentile` is 0-100, and the ends are inclusive,
 * so the largest value in a column always reads as the scale's last slot.
 */
export function fillAt(scale: (CellFill | undefined)[], percentile: number): CellFill | undefined {
	if (!scale.length) return undefined
	const clamped = Math.max(0, Math.min(100, percentile))
	return scale[Math.round((clamped / 100) * (scale.length - 1))]
}

/**
 * Which categorical slot each rule color is. That ramp pairs every hue family
 * as a dark member and a light partner. A cell is a ground rather than a mark,
 * so a rule takes the light one — red 10, green 4, amber 8. All three land
 * either side of the scale's middle stop, so a flagged cell reads level with a
 * mid-scale cell.
 *
 * Slots and not names: `paletteColors` hands out positions, and there is no way
 * to ask the ramp for "the green one". A reorder upstream is corrected here.
 */
const STATUS_SLOTS: Record<string, number> = { red: 10, green: 4, amber: 8 }

export function statusFill(colorName: string, tokens: ChartTokens): CellFill {
	const slot = STATUS_SLOTS[colorName?.toLowerCase()]
	const backgroundColor = slot ? tokens.categorical[slot - 1] : undefined
	if (!backgroundColor) {
		return { backgroundColor: 'var(--surface-gray-4)', color: 'var(--ink-gray-9)' }
	}
	return { backgroundColor, color: inkOn(backgroundColor, tokens) }
}
