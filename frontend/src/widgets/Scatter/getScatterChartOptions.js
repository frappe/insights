import { formatNumber } from '@/utils'
import { getColors } from '@/utils/colors'
import { inject } from 'vue'

export default function getScatterChartOptions(labels, datasets, options) {
	const $utils = inject('$utils')

	if (!labels?.length || !datasets?.length) {
		return {}
	}

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
		series: datasets.map((dataset, index) => ({
			name: dataset.label,
			data: dataset.data,
			color: colors[index],
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
