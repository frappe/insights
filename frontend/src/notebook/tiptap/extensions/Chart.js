import { createNodeExtension } from './utils'

import Chart from './Chart.vue'
export default createNodeExtension({
	name: 'chart',
	tag: 'chart',
	component: Chart,
	attributes: {
		chart_name: undefined,
	},
})
