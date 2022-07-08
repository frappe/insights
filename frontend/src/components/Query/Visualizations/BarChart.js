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
			maintainAspectRatio: false,
		}

		return () =>
			h(Bar, {
				chartData,
				chartOptions,
				cssClasses: 'flex items-center justify-center w-full px-6 py-4',
			})
	},
})
