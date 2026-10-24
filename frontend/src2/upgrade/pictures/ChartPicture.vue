<script setup lang="ts">
import { color } from 'echarts/core'
import { ChartCard, paletteColors, useChartTokens } from 'frappe-ui/charts'
import { computed, onMounted, ref } from 'vue'
import { adaptChart } from '../../charts/adapter'
import { makeChartRead } from '../../charts/chart_view'
import ChartChrome from '../../charts/components/ChartChrome.vue'

// A chart card as a dashboard shows it, with rows that never leave the page.
// It is the real card and the real adapter, so its look follows the app's.
const props = defineProps<{
	title: string
	/** A Line chart draws its area and a trend line. */
	type?: 'Bar' | 'Line'
	/** One reading per bar. */
	values?: number[]
	/** The bar a reader clicked: the others are drawn pale. */
	selected?: number
	/** The doctype the reader lacks: the card shows Not Permitted. */
	notPermitted?: string
}>()

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
// a trend line needs a time axis
const line = props.type === 'Line'

const config = {
	x_axis: {
		dimension: line
			? {
					dimension_name: 'month',
					column_name: 'month',
					data_type: 'Date',
					granularity: 'month',
			  }
			: { dimension_name: 'month', column_name: 'month', data_type: 'String' },
	},
	y_axis: {
		series: [
			{
				measure: {
					measure_name: 'amount',
					column_name: 'amount',
					data_type: 'Decimal',
					aggregation: 'sum',
				},
				...(line ? { show_area: true, show_trend_line: true } : {}),
			},
		],
	},
} as any

const result = {
	columns: [
		{ name: 'month', type: line ? 'Date' : 'String' },
		{ name: 'amount', type: 'Decimal' },
	],
	rows: (props.values ?? []).map((amount, index) => ({
		month: line ? `2026-0${(index % 9) + 1}-01` : MONTHS[index % MONTHS.length],
		amount,
	})),
} as any

const root = ref<HTMLElement>()
const { tokens } = useChartTokens(root)

// A picture is still: no bars growing in on every visit, and the picked bar
// stands out of the others.
const filler = computed(() => {
	if (props.notPermitted) return
	const adapted = adaptChart({
		chart_type: props.type ?? 'Bar',
		config,
		result,
		title: props.title,
		tokens: tokens.value,
		readonly: true,
	})
	if (!adapted) return
	// the one color a lone series draws in, and the same faded
	const [strong] = paletteColors(undefined, tokens.value, 1)
	const pale = color.modifyAlpha(strong, 0.35)
	const picked =
		props.selected === undefined
			? {}
			: {
					seriesConfig: {
						amount: {
							echartOptions: {
								itemStyle: {
									color: ({ dataIndex }: { dataIndex: number }) =>
										dataIndex === props.selected ? strong : pale,
								},
							},
						},
					},
			  }
	return {
		component: adapted.component,
		props: { ...adapted.props, ...picked, echartOptions: { animation: false } },
	}
})

const refused = props.notPermitted
	? makeChartRead({
			doc: {
				name: `upgrade-picture-${props.title}`,
				title: props.title,
				chart_type: 'Bar',
				can_write: false,
				config,
			},
			fetchData: async () => ({ not_permitted: { doctypes: [props.notPermitted!] } }) as any,
			fetchDrillData: () => Promise.reject(new Error('A picture has no rows behind it')),
	  })
	: undefined

onMounted(() => refused?.load())
</script>

<template>
	<ChartChrome v-if="refused" :chart="refused" readonly class="text-start" />
	<div v-else ref="root" class="h-full w-full text-start">
		<ChartCard class="h-full border-outline-gray-2 [--chart-card-inset:1rem]">
			<component :is="filler.component" v-if="filler" v-bind="filler.props" />
		</ChartCard>
	</div>
</template>
