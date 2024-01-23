import { formatNumber } from '@/utils'
import { getColors } from '@/utils/colors'
import { graphic } from 'echarts/core'
import { inject } from 'vue'
import { getShortNumber } from '@/utils'

export default function getLineChartOptions(labels, datasets, options) {
	if (!datasets || !datasets.length) {
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
		xAxis: {
			axisType: 'xAxis',
			type: 'category',
			axisTick: false,
			data: labels,
		},
		yAxis: datasets.map((dataset) => ({
			name: options.splitYAxis ? dataset.label : undefined,
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed' },
			},
			axisLabel: {
				formatter: (value, index) => getShortNumber(value, 1),
			},
		})),
		series: datasets.map((dataset, index) => ({
			name: dataset.label,
			data: dataset.data,
			type: 'line',
			yAxisIndex: options.splitYAxis ? index : 0,
			color: dataset.series_options.color || colors[index],
			smooth: dataset.series_options.smoothLines || options.smoothLines ? 0.4 : false,
			smoothMonotone: 'x',
			showSymbol: dataset.series_options.showPoints || options.showPoints,
			markLine: markLine,
			areaStyle:
				dataset.series_options.showArea || options.showArea
					? {
							color: new graphic.LinearGradient(0, 0, 0, 1, [
								{ offset: 0, color: dataset.series_options.color || colors[index] },
								{ offset: 1, color: '#fff' },
							]),
							opacity: 0.2,
					  }
					: undefined,
		})),
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
		tooltip: {
			trigger: 'axis',
			confine: true,
			appendToBody: false,
			valueFormatter: (value) => (isNaN(value) ? value : formatNumber(value)),
		},
	}
}
