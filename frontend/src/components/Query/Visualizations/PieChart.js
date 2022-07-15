import { defineComponent, h } from 'vue'
import { Pie } from 'vue-chartjs'
import { getRandomColor } from '@/controllers/visualization'
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement } from 'chart.js'

ChartJS.defaults.font.family = 'Inter'
ChartJS.defaults.font.style = 'inherit'
ChartJS.register(Title, Tooltip, Legend, ArcElement)

export default defineComponent({
	name: 'PieChart',
	components: { Pie },
	props: {
		data: {
			type: Object,
			required: true,
		},
	},
	setup(props) {
		const chartData = {
			labels: props.data.labels,
			datasets: props.data.datasets.map((dataset) => ({
				hoverOffset: 4,
				data: dataset.data,
				label: dataset.label,
				backgroundColor: getRandomColor(),
			})),
		}

		const chartOptions = {
			responsive: true,
			maintainAspectRatio: false,
			plugins: {
				legend: {
					position: 'bottom',
				},
			},
		}

		return () =>
			h(Pie, {
				chartData,
				chartOptions,
				cssClasses: 'flex justify-center w-full p-4',
			})
	},
})
