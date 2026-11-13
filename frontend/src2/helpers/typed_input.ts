// What a config form writes into a chart's config.
//
// The config is stored as JSON, so whatever a form hands it is what every
// reader gets. Two controls used to hand it something else. A number box handed
// back its text, and a cleared box handed back `''`, which is not absent to
// `??`. A picker handed back the whole dropdown option, with a `label` and a
// `value` into a slot that declares neither. Both are converted here, once,
// rather than at each of the fields.

import type { Dimension, DimensionOption } from '../types/query.types'

/** A number box's value as the number it names, or nothing at all. */
export function asNumber(value: unknown): number | undefined {
	if (value === '' || value === null || value === undefined) return undefined
	const number = Number(value)
	return Number.isFinite(number) ? number : undefined
}

/**
 * A picked option as the Dimension it names.
 *
 * An option is a Dimension plus what the dropdown shows it with. Naming the
 * Dimension's own keys is what keeps the dropdown's out: a key added to the
 * option reaches no config until it is named here.
 */
export function asDimension(option: DimensionOption | Dimension): Dimension {
	const dimension: Dimension = {
		dimension_name: option.dimension_name || option.column_name,
		column_name: option.column_name,
		data_type: option.data_type,
	}
	if (option.granularity) dimension.granularity = option.granularity
	if (option.windows) dimension.windows = option.windows
	return dimension
}
