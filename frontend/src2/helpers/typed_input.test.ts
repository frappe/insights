import { describe, expect, it } from 'vitest'
import { asDimension, asNumber } from './typed_input'

// The two controls that used to write untyped values into a chart's config: a
// number box, which handed back its text, and a dimension picker, which handed
// back the whole dropdown option.

describe('a number box', () => {
	// @feature charts.config-typed-values
	it('writes the number its text names', () => {
		expect(asNumber('100')).toBe(100)
		expect(asNumber('98.5')).toBe(98.5)
		expect(asNumber(0)).toBe(0)
	})

	// @feature charts.config-typed-values
	it('writes nothing once it is cleared, so the slot reads as absent', () => {
		expect(asNumber('')).toBeUndefined()
		expect(asNumber(null)).toBeUndefined()
		expect(asNumber(undefined)).toBeUndefined()
	})

	// @feature charts.config-typed-values
	it('writes nothing for text that names no number', () => {
		expect(asNumber('ten')).toBeUndefined()
		expect(asNumber(Infinity)).toBeUndefined()
	})
})

describe('a picked column', () => {
	// @feature charts.config-typed-values
	it('is written as the dimension, without what the dropdown showed it with', () => {
		expect(
			asDimension({
				dimension_name: 'Region',
				column_name: 'region',
				data_type: 'String',
				label: 'region',
				value: 'region',
			}),
		).toEqual({ dimension_name: 'Region', column_name: 'region', data_type: 'String' })
	})

	// @feature charts.config-typed-values
	it('keeps the grain and the spans the dimension itself has', () => {
		const dimension = asDimension({
			dimension_name: 'creation',
			column_name: 'creation',
			data_type: 'Datetime',
			granularity: 'week',
			label: 'creation',
			value: 'creation',
		})
		expect(dimension.granularity).toBe('week')
		expect('label' in dimension).toBe(false)
	})

	// @feature charts.config-typed-values
	it('is named by its column when the option names it nothing else', () => {
		expect(
			asDimension({
				dimension_name: '',
				column_name: 'status',
				data_type: 'String',
				label: 'status',
				value: 'status',
			}).dimension_name,
		).toBe('status')
	})
})
