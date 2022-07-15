import { Line } from 'vue-chartjs'
import { defineComponent, h } from 'vue'
import { getRandomColor } from '@/controllers/visualization'
import {
	Chart as ChartJS,
	Title,
	Tooltip,
	Legend,
	LineElement,
	CategoryScale,
	LinearScale,
	PointElement,
} from 'chart.js'

ChartJS.defaults.font.family = 'Inter'
ChartJS.defaults.font.style = 'inherit'
ChartJS.register(Title, Tooltip, Legend, LineElement, CategoryScale, LinearScale, PointElement)

export default defineComponent({
	name: 'LineChart',
	components: { Line },
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
				tension: 0,
				data: dataset.data,
				label: dataset.label,
				borderColor: getRandomColor(),
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
			h(Line, {
				chartData,
				chartOptions,
				cssClasses: 'flex justify-center w-full p-4',
			})
	},
})
