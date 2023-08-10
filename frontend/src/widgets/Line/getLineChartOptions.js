import { formatNumber } from '@/utils'
import { getColors } from '@/utils/colors'
import { inject } from 'vue'

export default function getLineChartOptions(labels, datasets, options) {
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
			top: 30,
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
		yAxis: datasets.map((dataset) => ({
			name: options.splitYAxis ? dataset.label : undefined,
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
			type: 'line',
			yAxisIndex: options.splitYAxis ? index : 0,
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
			trigger: 'axis',
			confine: true,
			appendToBody: false,
			valueFormatter: (value) => (isNaN(value) ? value : formatNumber(value)),
		},
	}
}
