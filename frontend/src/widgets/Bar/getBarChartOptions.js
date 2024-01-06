import { formatNumber } from '@/utils'
import { getColors } from '@/utils/colors'
import { inject } from 'vue'

export default function getBarChartOptions(labels, datasets, options) {
	const $utils = inject('$utils')

	if (!labels?.length || !datasets?.length) {
		return {}
	}

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
				// interval: 0,
				formatter: (value, index) =>
					!isNaN(value) ? $utils.getShortNumber(value, 1) : $utils.ellipsis(value, 20),
			},
		},
		{
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed' },
			},
			axisLabel: {
				formatter: (value, index) =>
					!isNaN(value) ? $utils.getShortNumber(value, 1) : $utils.ellipsis(value, 20),
			},
		},
	]

	const colors = options.colors?.length ? [...options.colors, ...getColors()] : getColors()

	return {
		animation: false,
		color: colors,
		grid: {
			top: 15,
			bottom: 35,
			left: 25,
			right: 35,
			containLabel: true,
		},
		xAxis: options.invertAxis ? axes[1] : axes[0],
		yAxis: options.invertAxis ? axes[0] : axes[1],
		series: datasets.map((dataset, index) => ({
			type: 'bar',
			name: dataset.label,
			barMaxWidth: 50,
			data: options.invertAxis ? dataset.data.reverse() : dataset.data,
			itemStyle: {
				borderRadius: options.invertAxis ? [0, 4, 4, 0] : [4, 4, 0, 0],
			},
			markLine: markLine,
			stack: options.stack ? 'stack' : null,
			color: dataset.series_options.color || colors[index],
		})),
		tooltip: {
			trigger: 'axis',
			confine: true,
			appendToBody: false,
			valueFormatter: (value) => (isNaN(value) ? value : formatNumber(value)),
		},
		legend: {
			icon: 'circle',
			type: 'scroll',
			bottom: 'bottom',
			pageIconSize: 12,
			pageIconColor: '#64748B',
			pageIconInactiveColor: '#C0CCDA',
			pageFormatter: '{current}',
			pageButtonItemGap: 2,
		},
	}
}
