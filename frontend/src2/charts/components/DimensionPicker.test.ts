import { describe, expect, it } from 'vitest'
import { createSSRApp, h, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'
import type { Dimension } from '../../types/query.types'
import DimensionPicker from './DimensionPicker.vue'

// The picker gives a date dimension a grain when it has none, on the x axis of
// an axis chart and everywhere else. Only the x axis may follow the span.

async function picked(dimension: Dimension, autoGranularity: boolean) {
	const model = reactive({ dimension })
	const app = createSSRApp({
		render: () =>
			h(DimensionPicker, {
				options: [],
				autoGranularity,
				modelValue: model.dimension,
				'onUpdate:modelValue': (value: Dimension) => (model.dimension = value),
			}),
	})
	app.config.globalProperties.__ = (text: string) => text
	app.config.warnHandler = () => {}
	await renderToString(app)
	return model.dimension.granularity
}

const date = (granularity?: Dimension['granularity']): Dimension => ({
	column_name: 'posting_date',
	dimension_name: 'posting_date',
	data_type: 'Date',
	...(granularity ? { granularity } : {}),
})

describe('a date column picked for a chart', () => {
	// @feature charts.auto-grain
	it('follows the span on an x axis, keeps the grain an existing axis was saved at, and is monthly elsewhere', async () => {
		expect(await picked(date(), true)).toBe('auto')
		expect(await picked(date('month'), true)).toBe('month')
		expect(await picked(date(), false)).toBe('month')
		expect(await picked(date('auto'), false)).toBe('month')
	})
})
