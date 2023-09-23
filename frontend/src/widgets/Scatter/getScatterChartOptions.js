import { formatNumber } from '@/utils'
import { getColors } from '@/utils/colors'
import { inject } from 'vue'

export default function getScatterChartOptions(labels, datasets, options) {
	const $utils = inject('$utils')

	if (!labels?.length || !datasets?.length) {
		return {}
	}

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
			splitLine: {
				show: true,
				lineStyle: { type: 'dashed' },
			},
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
			type: 'scatter',
			symbolSize: 10,
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
			appendToBody: true,
			valueFormatter: (value) => (isNaN(value) ? value : formatNumber(value)),
		},
	}
}
