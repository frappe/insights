import { formatNumber, getFormatUnits, getShortNumber } from '../helpers'
import type { NumberFormat } from '../types/chart.types'
import type { DataFormat } from '../types/query.types'

/**
 * Insights' one number-format policy.
 *
 * Everything that prints a measured number asks this module how — every chart
 * adapter, and the grid. A chart passes what it gets back to v2's `format`
 * prop, so the library owns the drawing and Insights owns the policy. Nothing
 * else formats a number of its own.
 *
 * ## The layers
 *
 * Four things have a say, and each one overrides the last, key by key:
 *
 *   1. the locale, which groups the digits and picks a precision;
 *   2. the Measure's own unit — a currency prints the site's symbol, a percent
 *      is scaled by 100 and prints `%`;
 *   3. the chart's `number_format`, the default every value of it inherits;
 *   4. the Measure's `number_formats` entry, which is that value's own.
 *
 * A layer overrides a key it states, including with an empty string: an author
 * who cleared a prefix meant to clear it. What it does not state, it leaves to
 * the layer under it.
 *
 * The scale is the exception: it is arithmetic, not display, so a percent
 * Measure is scaled whatever the layers above it print.
 *
 * ## Old spellings
 *
 * `shorten_numbers` and `compact_numbers` are read as `shorten`, and `decimal`
 * as `decimals`, wherever an earlier release wrote them. They are read, never
 * written: the forms write `number_format` and `number_formats` alone, and no
 * stored config is rewritten to reach them.
 */

/** Prints one measured number. This is what v2 calls `format`. */
// eslint-disable-next-line no-unused-vars
export type NumberFormatter = (value: number) => string

/**
 * A Measure, as the formatter reads it: what it is called, and the unit it
 * states. Structural, so a grid column — which has a name and a unit and no
 * Measure behind it — resolves through the same call.
 */
export type FormattedMeasure = {
	measure_name?: string
	format?: DataFormat
}

/** The spellings earlier releases wrote the same three settings under. */
type NumberFormatAliases = {
	shorten_numbers?: boolean
	compact_numbers?: boolean
	decimal?: number
}

/** One layer, in either spelling. */
export type NumberFormatSource = NumberFormat & NumberFormatAliases

/**
 * Whatever states a format: a Chart's config, or a bare `NumberFormat`. A
 * config carries the chart-level default and the per-Measure overrides. A bare
 * format carries neither, and reads as one layer.
 */
export type NumberFormatConfigSource = NumberFormatSource & {
	number_format?: NumberFormatSource
	number_formats?: Record<string, NumberFormatSource>
	/** Number chart, before the map: one entry per value, in the order below. */
	number_column_options?: NumberFormatSource[]
	number_columns?: { measure_name?: string }[]
}

/** A format with nothing left to fall back on. */
export type ResolvedNumberFormat = NumberFormat & {
	/** What the stored number is multiplied by before it prints. */
	scale: number
}

/** What a shortened number carries when nobody says. v2's own default. */
const SHORT_DECIMALS = 1

/**
 * The format one Measure of a chart prints in, with every layer merged.
 *
 * Charts hand the formatter to v2 and never see this. The Number card does:
 * v2's card takes the prefix, the suffix and the precision as props of its own,
 * because it prints a target and a delta beside the reading and formats all
 * three alike. So the pieces are exported, and the card maps them across.
 */
export function numberFormatOf(
	config?: NumberFormatConfigSource | null,
	measure?: FormattedMeasure | null,
): ResolvedNumberFormat {
	const unit = getFormatUnits(measure?.format)
	const merged = mergeFormats([
		{ prefix: unit.prefix, suffix: unit.suffix },
		readNumberFormat(config),
		readNumberFormat(config?.number_format),
		readNumberFormat(valueFormatOf(config, measure)),
		readNumberFormat(measure?.measure_name ? config?.number_formats?.[measure.measure_name] : null),
	])
	return { ...merged, scale: unit.scale }
}

/**
 * What a form field inherits: every layer under the one that field writes.
 *
 * A panel field shows this as its placeholder, so an author reads what a key it
 * does not state will print as. The Measure's own unit is not in it — this
 * takes a config and a name, and a unit needs the Measure itself.
 */
export function inheritedNumberFormat(
	config?: NumberFormatConfigSource | null,
	measureName?: string,
): NumberFormat {
	const layers = [readNumberFormat(config)]
	if (measureName) {
		layers.push(readNumberFormat(config?.number_format))
		layers.push(readNumberFormat(valueFormatOf(config, { measure_name: measureName })))
	}

	return mergeFormats(layers)
}

/**
 * The precision an unstated one prints as, under the format in effect.
 *
 * A shortened number falls back to one place. An unshortened one leaves the
 * places to the locale, which no single number states, so this names none.
 *
 * A field shows this when it inherits no precision of its own. It takes the
 * effective `shorten` rather than reading a layer, because a form states that
 * toggle beside the precision — the two are one layer's answer, and the field
 * has to show what its own toggle already implies.
 */
export function defaultDecimals(shorten?: boolean): number | undefined {
	return shorten ? SHORT_DECIMALS : undefined
}

/** The one resolver. Every chart and the grid print their numbers with this. */
export function numberFormatter(
	config?: NumberFormatConfigSource | null,
	measure?: FormattedMeasure | null,
): NumberFormatter {
	const format = numberFormatOf(config, measure)
	return (value: any) => printNumber(value, format)
}

/** One number, under a format already resolved. */
export function printNumber(value: any, format: ResolvedNumberFormat): string {
	if (value === null || value === undefined || value === '') return ''
	const number = Number(value)
	if (isNaN(number)) return ''

	const scaled = number * format.scale
	const printed = format.shorten
		? getShortNumber(scaled, format.decimals ?? SHORT_DECIMALS)
		: formatNumber(scaled, format.decimals)
	return `${format.prefix ?? ''}${printed}${format.suffix ?? ''}`
}

/**
 * One layer, read out of whatever wrote it. The current spelling wins over the
 * old one, so a value that states both prints what its form last showed.
 */
export function readNumberFormat(source?: NumberFormatSource | null): NumberFormat {
	if (!source) return {}
	const format: NumberFormat = {}

	if (stated(source.shorten)) format.shorten = source.shorten
	else if (stated(source.shorten_numbers)) format.shorten = source.shorten_numbers
	else if (stated(source.compact_numbers)) format.shorten = source.compact_numbers

	const decimals = toDecimals(source.decimals) ?? toDecimals(source.decimal)
	if (decimals !== undefined) format.decimals = decimals

	if (stated(source.prefix)) format.prefix = source.prefix
	if (stated(source.suffix)) format.suffix = source.suffix

	return format
}

/** This Measure's own layer, wherever the chart type keeps it. */
function valueFormatOf(
	config?: NumberFormatConfigSource | null,
	measure?: FormattedMeasure | null,
): NumberFormatSource | undefined {
	const name = measure?.measure_name
	if (!config || !name) return
	// The Number chart kept a value's settings beside its Measure, by position.
	const index = (config.number_columns || []).findIndex(
		(column) => column?.measure_name === name,
	)
	return index === -1 ? undefined : config.number_column_options?.[index]
}

/** Least specific first. A later layer wins on every key it states. */
function mergeFormats(layers: NumberFormat[]): NumberFormat {
	const merged: NumberFormat = {}
	for (const layer of layers) {
		for (const key of Object.keys(layer) as (keyof NumberFormat)[]) {
			const value = layer[key]
			if (value !== undefined) (merged as any)[key] = value
		}
	}
	return merged
}

/** A layer states a key when it holds anything but nothing. `''` is a value. */
function stated(value: unknown): boolean {
	return value !== undefined && value !== null
}

/** What `Intl.NumberFormat` accepts. Outside it, the constructor throws. */
const MIN_DECIMALS = 0
const MAX_DECIMALS = 20

/**
 * A number control hands back a string, and an empty one when it is cleared.
 * Cleared means unset — unlike a cleared prefix, which means no prefix.
 *
 * A precision outside the range above throws where the number prints, which
 * takes down the whole chart rather than one value. Clamping here covers every
 * layer and every config already stored, so nothing downstream checks again.
 */
function toDecimals(value: unknown): number | undefined {
	if (!stated(value) || value === '') return undefined
	const decimals = Number(value)
	if (isNaN(decimals)) return undefined
	return Math.min(MAX_DECIMALS, Math.max(MIN_DECIMALS, Math.floor(decimals)))
}
