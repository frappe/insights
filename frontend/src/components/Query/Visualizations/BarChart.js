import { Bar } from 'vue-chartjs'
import { defineComponent, h } from 'vue'
import { getRandomColor } from '@/controllers/visualization'
import {
	Chart as ChartJS,
	Title,
	Tooltip,
	Legend,
	BarElement,
	CategoryScale,
	LinearScale,
} from 'chart.js'

ChartJS.defaults.font.family = 'Inter'
ChartJS.defaults.font.style = 'inherit'
ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

export default defineComponent({
	name: 'BarChart',
	components: { Bar },
	props: {
		data: {
			type: Object,
			required: true,
		},
	},
	setup(props) {
		console.log(props)
		const chartData = {
			labels: props.data.labels,
			datasets: props.data.datasets.map((dataset) => ({
				data: dataset.data,
				label: dataset.label,
				backgroundColor: getRandomColor(),
			})),
		}

		const chartOptions = {
			responsive: true,
			maintainAspectRatio: true,
			plugins: {
				legend: {
					position: 'bottom',
				},
			},
		}

		return () =>
			h(Bar, {
				chartData,
				chartOptions,
				width: 600,
				height: 300,
				cssClasses: 'flex justify-center w-full',
			})
	},
})
