import { getColors } from '@/utils/colors'
import { inject } from 'vue'

export default function getBarChartOptions(labels, datasets, options) {
	const $utils = inject('$utils')

	const markLine = options.referenceLine
		? {
				data: [
					{
						name: options.referenceLine,
						type: options.referenceLine.toLowerCase(),
						label: { position: 'middle', formatter: '{b}: {c}' },
					},
				],
		  }
		: {}

	const axes = [
		{
			type: 'category',
			data: options.invertAxis ? labels.reverse() : labels,
			axisTick: false,
			axisLabel: {
				rotate: options.rotateLabels,
				interval: 0,
			},
			axisLabel: {
				formatter: (value, index) =>
					!isNaN(value) ? $utils.getShortNumber(value, 1) : value,
			},
		},
		{
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed' },
			},
			axisLabel: {
				formatter: (value, index) =>
					!isNaN(value) ? $utils.getShortNumber(value, 1) : value,
			},
		},
	]

	return {
		animation: false,
		color: options.colors || getColors(),
		grid: {
			top: 25,
			bottom: 35,
			left: 20,
			right: 30,
			containLabel: true,
		},
		xAxis: options.invertAxis ? axes[1] : axes[0],
		yAxis: options.invertAxis ? axes[0] : axes[1],
		series: datasets.map((dataset) => ({
			type: 'bar',
			name: dataset.label,
			barMaxWidth: 50,
			data: options.invertAxis ? dataset.data.reverse() : dataset.data,
			itemStyle: {
				borderRadius: options.invertAxis ? [0, 4, 4, 0] : [4, 4, 0, 0],
			},
			markLine: markLine,
			stack: options.stack ? 'stack' : null,
			itemStyle: {
				borderRadius: options.invertAxis ? [0, 4, 4, 0] : [4, 4, 0, 0],
			},
		})),
		tooltip: {
			trigger: 'axis',
			confine: true,
			appendToBody: false,
			valueFormatter: (value) => (isNaN(value) ? value : value.toLocaleString()),
		},
	}
}
