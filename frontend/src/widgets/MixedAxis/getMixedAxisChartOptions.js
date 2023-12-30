import { formatNumber } from '@/utils'
import { getColors } from '@/utils/colors'
import { inject } from 'vue'

export default function getMixedAxisChartOptions(labels, datasets, options) {
	const $utils = inject('$utils')

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

	return {
		animation: false,
		color: options.colors || getColors(),
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
			nameLocation: 'middle',
			nameGap: 45,
			nameTextStyle: { color: 'transparent' },
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed' },
			},
			axisLabel: {
				formatter: (value, index) => $utils.getShortNumber(value, 1),
			},
		})),
		series: datasets.map((dataset, index) => ({
			name: dataset.label,
			data: dataset.data,
			type: dataset.series_options.type,
			color: dataset.series_options.color,
			yAxisIndex: options.splitYAxis ? index : 0,
			smooth: dataset.series_options.smoothLines ? 0.4 : false,
			smoothMonotone: 'x',
			showSymbol: dataset.series_options.showPoints,
			markLine: markLine,
			areaStyle: { opacity: dataset.series_options.showArea ? 0.1 : 0 },
			itemStyle: {
				borderRadius: options.invertAxis ? [0, 4, 4, 0] : [4, 4, 0, 0],
			},
			barMaxWidth: 50,
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
