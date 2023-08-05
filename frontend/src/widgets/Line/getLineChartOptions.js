import { getColors } from '@/utils/colors'
import { inject } from 'vue'

export default function getLineChartOptions(labels, datasets, options) {
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
		xAxis: {
			axisType: 'xAxis',
			type: 'category',
			axisTick: false,
			data: labels,
		},
		yAxis: {
			axisType: 'yAxis',
			type: 'value',
			splitLine: {
				lineStyle: { type: 'dashed' },
			},
			axisLabel: {
				formatter: (value, index) => $utils.getShortNumber(value, 1),
			},
		},
		series: datasets.map((dataset) => ({
			name: dataset.label,
			data: dataset.data,
			type: 'line',
			smooth: options.smoothLines ? 0.4 : false,
			smoothMonotone: 'x',
			showSymbol: options.showPoints,
			markLine: markLine,
			areaStyle: { opacity: options.showArea ? 0.1 : 0 },
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
			trigger: 'item',
			confine: true,
			appendToBody: true,
			valueFormatter: (value) => (isNaN(value) ? value : value.toLocaleString()),
		},
	}
}
