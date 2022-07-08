import { defineComponent, h } from 'vue'
import { Pie } from 'vue-chartjs'
import { getRandomColor } from '@/controllers/visualization'
import { Chart as ChartJS, Title, Tooltip, Legend, ArcElement } from 'chart.js'

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
		}

		return () =>
			h(Pie, {
				chartData,
				chartOptions,
				cssClasses: 'flex items-center justify-center w-full px-6 py-4',
			})
	},
})
