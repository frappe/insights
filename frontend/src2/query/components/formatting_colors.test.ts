import { describe, expect, it } from 'vitest'
import type { ChartTokens } from 'frappe-ui/charts'
import { colorScaleDirection, fillAt, magnitudeScale, statusFill } from './formatting_colors'

const tokens = {
	categorical: [
		'#2283c3',
		'#84c5f9',
		'#289e60',
		'#84d4a1',
		'#753cbb',
		'#bb9df1',
		'#c98c28',
		'#f5ca8e',
		'#bd2040',
		'#fc8e94',
	],
	sequential: [
		'#095895',
		'#2283c3',
		'#4eacdf',
		'#71bde5',
		'#91ccec',
		'#9cd1ee',
		'#b8def2',
		'#dceef9',
		'#edf7fc',
	],
	diverging: [
		'#366ea3',
		'#5b8ec1',
		'#81b0de',
		'#a9d2fb',
		'#fbf1c7',
		'#eec88c',
		'#e09e62',
		'#ce7249',
		'#b5473f',
	],
	insideLabel: '#2d2d2d',
} as ChartTokens

describe('color scale direction', () => {
	it('reads the two names the option carried when the scale ran red to green', () => {
		expect(colorScaleDirection('Green-Red')).toBe('ascending')
		expect(colorScaleDirection('Red-Green')).toBe('descending')
	})

	it('falls back to deeper for higher values', () => {
		expect(colorScaleDirection(undefined)).toBe('ascending')
		expect(colorScaleDirection('nonsense')).toBe('ascending')
	})
})

describe('the magnitude scale', () => {
	const scale = magnitudeScale(tokens, 'ascending')

	it('draws nothing at the bottom of the range', () => {
		expect(scale[0]).toBeUndefined()
		expect(scale.slice(1).every(Boolean)).toBe(true)
	})

	it('spends one hue and every stop of it', () => {
		expect(scale.slice(1).map((f) => f!.backgroundColor)).toEqual(
			tokens.sequential.slice().reverse(),
		)
	})

	it('runs pale to deep', () => {
		expect(scale[1]!.backgroundColor).toBe('#edf7fc')
		expect(scale[scale.length - 1]!.backgroundColor).toBe('#095895')
	})

	it('puts the deep end at the bottom when the rule asks', () => {
		const down = magnitudeScale(tokens, 'descending')
		expect(down[0]!.backgroundColor).toBe('#095895')
		expect(down[down.length - 1]).toBeUndefined()
	})

	it('turns the ink white only where a fill is dark', () => {
		const inks = scale.slice(1).map((f) => f!.color)
		expect(inks.filter((c) => c === '#ffffff')).toHaveLength(2)
		expect(inks[0]).toBe(tokens.insideLabel)
	})
})

describe('picking a stop', () => {
	const scale = magnitudeScale(tokens, 'ascending')

	it('lands on the ends', () => {
		expect(fillAt(scale, 0)).toBeUndefined()
		expect(fillAt(scale, 100)).toBe(scale[scale.length - 1])
	})

	it('clamps a percentile outside the range', () => {
		expect(fillAt(scale, -20)).toBeUndefined()
		expect(fillAt(scale, 180)).toBe(scale[scale.length - 1])
	})

	it('has nothing to pick from an empty scale', () => {
		expect(fillAt([], 50)).toBeUndefined()
	})
})

describe('rule fills', () => {
	it("picks each Jewel family's light partner, because a cell is a ground", () => {
		expect(statusFill('red', tokens).backgroundColor).toBe(tokens.categorical[9])
		expect(statusFill('green', tokens).backgroundColor).toBe(tokens.categorical[3])
		expect(statusFill('amber', tokens).backgroundColor).toBe(tokens.categorical[7])
	})

	it('inks a rule fill by the one rule every fill follows', () => {
		for (const name of ['red', 'green', 'amber']) {
			expect(statusFill(name, tokens).color).toBe(tokens.insideLabel)
		}
	})

	it('reads a color name whatever case it was written in', () => {
		expect(statusFill('Green', tokens)).toEqual(statusFill('green', tokens))
	})

	it('falls back to a neutral fill for a name it does not know', () => {
		expect(statusFill('chartreuse', tokens).backgroundColor).toBe('var(--surface-gray-4)')
		expect(statusFill('', tokens).backgroundColor).toBe('var(--surface-gray-4)')
	})

	it('falls back when the ramp is too short to hold the slot', () => {
		const short = { ...tokens, categorical: ['#2283c3', '#84c5f9'] } as typeof tokens
		expect(statusFill('red', short).backgroundColor).toBe('var(--surface-gray-4)')
	})
})
