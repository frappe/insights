import { ellipsis, formatNumber } from '@/utils'
import { getColors } from '@/utils/colors'

export default function getPieChartOptions(labels, dataset, options) {
	const MAX_SLICES = 9

	if (!labels?.length || !dataset?.data?.length) {
		return {}
	}

	const colors = options.colors?.length ? [...options.colors, ...getColors()] : getColors()

	const slices = dataset.data.slice(0, parseInt(options.maxSlices) || MAX_SLICES)
	const otherSlices = dataset.data
		.slice(parseInt(options.maxSlices) || 9)
		.reduce((a, b) => a + b, 0)
	const data = slices.map((value, index) => {
		return {
			name: labels[index],
			value: value,
			itemStyle: {
				color: colors[index],
			},
		}
	})
	if (otherSlices) {
		data.push({
			name: 'Others',
			value: otherSlices,
			itemStyle: { color: colors[slices.length] },
		})
	}

	const legendOptions = { type: 'plain', bottom: 0 }
	let center = ['50%', '50%']
	let radius = ['40%', '70%']

	if (!options.inlineLabels && options.labelPosition) {
		const position = options.labelPosition
		updateLegendOptions(position.value ?? position)
	}

	function updateLegendOptions(position) {
		legendOptions.type = options.scrollLabels ? 'scroll' : 'plain'
		legendOptions.orient =
			position === 'Top' || position === 'Bottom' ? 'horizontal' : 'vertical'

		switch (position) {
			case 'Top':
				radius = ['40%', '70%']
				legendOptions.top = 0
				legendOptions.left = 'center'
				center = ['50%', '60%']
				legendOptions.padding = 20
				break
			case 'Bottom':
				radius = ['40%', '70%']
				legendOptions.bottom = 0
				legendOptions.left = 'center'
				center = ['50%', '43%']
				legendOptions.padding = [20, 20, 10, 20]
				break
			case 'Right':
				radius = ['45%', '80%']
				center = ['33%', '50%']
				legendOptions.left = '63%'
				legendOptions.top = 'middle'
				legendOptions.padding = [20, 0, 20, 0]
				break
			case 'Left':
				radius = ['45%', '80%']
				center = ['67%', '50%']
				legendOptions.right = '63%'
				legendOptions.top = 'middle'
				legendOptions.padding = [20, 0, 20, 0]
				break
		}
	}

	function formatLabel({ name, percent }) {
		return `${ellipsis(name, 20)} (${percent.toFixed(0)}%)`
	}

	function formatLegend(name) {
		let total = dataset.data.reduce((a, b) => a + b, 0)
		const labelIndex = labels.indexOf(name)

		if (labelIndex === -1 && name == 'Others') {
			const otherSlicesTotal = dataset.data
				.slice(parseInt(options.maxSlices) || MAX_SLICES)
				.reduce((a, b) => a + b, 0)
			const percent = (otherSlicesTotal / total) * 100
			return `${ellipsis(name, 20)} (${percent.toFixed(0)}%)`
		}

		const percent = (dataset.data[labelIndex] / total) * 100
		return `${ellipsis(name, 20)} (${percent.toFixed(0)}%)`
	}

	function appendPercentage(value) {
		let total = dataset.data.reduce((a, b) => a + b, 0)
		const percent = (value / total) * 100
		return `${formatNumber(value, 2)} (${percent.toFixed(0)}%)`
	}

	return {
		animation: false,
		color: colors,
		series: [
			{
				type: 'pie',
				name: dataset.label,
				data: data,
				center: center,
				radius: radius,
				labelLine: {
					show: options.inlineLabels,
					lineStyle: {
						width: 2,
					},
					length: 10,
					length2: 20,
					smooth: true,
				},
				label: {
					show: options.inlineLabels,
					formatter: formatLabel,
				},
				emphasis: {
					scaleSize: 5,
				},
			},
		],
		tooltip: {
			trigger: 'item',
			confine: true,
			appendToBody: false,
			valueFormatter: appendPercentage,
		},
		legend: !options.inlineLabels
			? {
					type: 'plain',
					icon: 'circle',
					pageIconSize: 12,
					pageIconColor: '#64748B',
					pageIconInactiveColor: '#C0CCDA',
					pageFormatter: '{current}',
					pageButtonItemGap: 2,
					...legendOptions,
					formatter: formatLegend,
			  }
			: undefined,
	}
}
