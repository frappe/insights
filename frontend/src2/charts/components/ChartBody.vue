<script setup lang="ts">
import DOMPurify from 'dompurify'
import { Button } from 'frappe-ui'
import { ChartContainer } from 'frappe-ui/charts'
import { AlertTriangle, RefreshCcw } from 'lucide-vue-next'
import { computed, shallowRef } from 'vue'
import { __ } from '../../translation'
import { EMPTY_RESULT } from '../../query/helpers'
import { adaptChart, drawsOwnCards, type ChartStateProps, type DrillDownTarget } from '../adapter'
import { ChartRead } from '../chart_read'
import { segmentClickEvents, type ChartSegmentClick, type ClickPoint } from '../drill/segment_click'
import ChartSectionEmptySvg from './ChartSectionEmptySvg.vue'

// The chart itself: the type it is, the data it has, and every state in between.
// One state machine — a surface that draws a chart draws this, and gets the
// failure, the reload and the empty result along with the picture. Segment
// clicks are reported, never handled — drill-down is a dialog the caller offers,
// so it is the caller that carries it.
//
// It draws no card. The border, the padding and the title belong to whoever
// frames the chart: `ChartCardFrame` on an Insights page, the widget frame on a
// desk workspace. A host that has one mounts this and gets the chart alone.
//
// The states are frappe-ui's, and what goes inside them is the adapter's answer:
// it says which component draws this Chart and what to hand it, so nothing here
// switches on chart type. A new type is added in `charts/adapter`, not here.
//
// Where the states are drawn is the one thing that varies, and the adapter
// answers that too. A type with no card of its own wears them on the chrome
// around the plot. A type that draws cards — a Number Chart's readings are cards
// already — wears them inside each card, so it is mounted in every state and
// handed `ChartStateProps` instead.
//
// `readonly` is for a surface that cannot change the chart. It decides two
// things, and they are the same thing: a table's sort rewrites the chart's config
// and re-runs its query, which a reader holds neither half of, so the control is
// not offered rather than offered and dead — and for the same reason a reader is
// told about the data ("No data") where an author is told about the config.
const props = defineProps<{
	chart: ChartRead
	// heads the chart. Left out, no title is drawn anywhere in it — which is what
	// a host that prints its own asks for.
	title?: string
	// which reading to draw, for a Number Chart. A host that draws one reading per
	// cell says which. One that draws the chart says nothing and gets them all.
	column?: string
	readonly?: boolean
	// whether filters narrowed the rows, so an empty card can offer to clear them.
	// Only a surface that owns filter state can say, and only it can reset them.
	filtered?: boolean
}>()
const emit = defineEmits<{
	// where the reader pointed, for a surface that offers the drill menu
	segmentClick: [click: ChartSegmentClick]
	resetFilters: []
}>()

const chart_type = computed(() => props.chart.doc.chart_type)
const config = computed(() => props.chart.doc.config)
const result = computed(() => props.chart.result || { ...EMPTY_RESULT })

// Whether the filler draws the states itself. A property of the chart type, so
// it is settled before there is a result to adapt.
const ownsStates = computed(() => drawsOwnCards(chart_type.value))

const filler = computed(() => {
	// the result outlives a chart type switch, so without this the adapter would
	// run against the incoming type's still-empty config
	if (props.chart.configErrors.length) return
	// A filler that owns its states is built from the config alone: its grid has
	// to stand while the query runs and stand when the query fails.
	if (!result.value.columns?.length && !ownsStates.value) return
	return adaptChart({
		chart_type: chart_type.value,
		config: config.value,
		result: result.value,
		recordLinks: props.chart.recordLinks,
		sparklineResult: props.chart.sparklineResult,
		title: props.title,
		column: props.column,
		readonly: props.readonly,
		executing: props.chart.executing,
	})
})

// A table keeps its rows while the next run is in flight. Other types blank. A
// table on a filtered dashboard would otherwise blank on every filter move.
const keepsLastPicture = computed(
	() => chart_type.value === 'Table' && Boolean(result.value.rows?.length),
)

// What the card shows, in the order the store settles it: a failure outranks the
// reload that would replace it, and a reload outranks the rows it is replacing.
// `unconfigured` is the state a chart is born in and the state a config the
// server refused puts it back in — nothing is drawn, and the space the picture
// would take is where the reason is printed.
const state = computed(() => {
	if (props.chart.failed) return props.chart.serverBusy ? 'serverBusy' : 'failed'
	if (props.chart.executing && !keepsLastPicture.value) return 'loading'
	if (props.chart.configErrors.length) return 'unconfigured'
	if (props.chart.empty) return 'empty'
	return filler.value ? 'chart' : 'unconfigured'
})

// What an author has left to fill in, printed where the picture would be. It is
// the same line a chart nobody has configured yet shows, so a half-configured
// chart says what is missing rather than repeating the invitation. A reader owns
// no config, so they are never told about one.
const unconfigured = computed(() => {
	const errors = props.chart.configErrors
	if (props.readonly || !errors.length) {
		return [__('Pick a chart type and configure options to see the chart here')]
	}
	return errors
})

// Any non-empty string puts the container in its error state. The slot below
// draws the block itself, because a retry belongs beside the message.
//
// The headline names what happened and the detail names why. They are two lines
// and not one because a card can be short enough to hold only one of them, and
// then the line to keep is the one every reader can act on. The detail is what
// gives way, in this block and in a card that draws the failure itself.
//
// The headline is short enough for the narrowest surface that draws it, which is
// one reading of a Number Chart. One line for both, rather than a second string
// that says the same thing in fewer words.
const headline = computed(() => {
	if (state.value === 'serverBusy') return __('The server is busy')
	if (state.value === 'failed') return __('Could not load')
	return null
})

// What the server said. An author can act on it. A reader owns neither the query
// nor the config it names, so a reader gets the headline alone.
const detail = computed(() => {
	if (state.value !== 'failed' || props.readonly) return ''
	return props.chart.failure
})

// A Frappe exception message carries markup — a link to the docs, a `<br>` — so
// the detail is drawn as HTML and not as its own source. DOMPurify is what keeps
// a message that reached the server from a user out of the DOM as script.
const detailHtml = computed(() => (detail.value ? DOMPurify.sanitize(detail.value) : ''))
// The tooltip holds the whole message, which an element attribute can only carry
// as text. Stripping every tag is the same sanitize with nothing allowed through.
const detailText = computed(() =>
	detail.value ? DOMPurify.sanitize(detail.value, { ALLOWED_TAGS: [] }) : undefined,
)

// What a filler that owns its states is told, bound as props beside the rest of
// its input. Nothing here knows which component reads them.
const stateProps = computed(() => {
	if (!ownsStates.value) return {}
	const owned: ChartStateProps = {
		loading: state.value === 'loading',
		failure: headline.value
			? {
					headline: headline.value,
					detailHtml: detailHtml.value,
					detailText: detailText.value,
			  }
			: null,
		onRetry: () => props.chart.load(true),
	}
	return owned
})

// The events a filler reports a click through, bound without knowing which chart
// type emits which. The adapter names them and turns each payload into the point
// behind it.
const fillerEvents = computed(() =>
	segmentClickEvents(filler.value, result.value.columns, reportSegment),
)

// echarts hands over the datapoint and not the event that reached it, so the
// point the menu opens at is read off the click on its way in. The capture phase
// is what puts it there before the chart's own handler runs.
const clickedAt = shallowRef<ClickPoint>({ x: 0, y: 0 })
function rememberPoint(event: MouseEvent) {
	clickedAt.value = { x: event.clientX, y: event.clientY }
}

// A resolver answers with the raw row, which is what a drill reads, so nothing
// is looked up on the way out.
function reportSegment(target: DrillDownTarget) {
	emit('segmentClick', { target, point: clickedAt.value })
}
</script>

<template>
	<div class="h-full w-full" data-testid="chart" @click.capture="rememberPoint">
		<component
			v-if="filler && (state === 'chart' || ownsStates)"
			:is="filler.component"
			v-bind="{ ...filler.props, ...stateProps }"
			v-on="fillerEvents"
		/>

		<!-- Every state but the picture. `#loading` is left alone: v2 draws a
		     skeleton the size of the plot, which is what a chart still filling in
		     should read as to a reader and to an author alike. -->
		<ChartContainer
			v-else
			:title="props.title"
			:loading="state === 'loading'"
			:error="headline"
			:empty="true"
		>
			<!-- the queue turns a card away rather than queueing it, so asking
			     again is the whole remedy — and a chart that failed for any
			     other reason is worth one more try too -->
			<template #error>
				<!-- One block, so the headline and the action hold their size and
				     the detail is the only thing a short box takes back. `status`
				     and not `alert`: a dashboard can fail eight cards at once, and
				     eight interruptions say less than one line each. -->
				<div class="flex min-h-0 w-full flex-col items-center gap-2" role="status">
					<div class="flex shrink-0 items-center gap-1.5 text-p-sm text-ink-gray-8">
						<!-- The size of the text it stands beside, here and in every
						     other failure Insights draws: an icon larger than its
						     sentence reads as a picture of an error, not as part of
						     the line that states one. -->
						<AlertTriangle
							class="h-3.5 w-3.5 shrink-0 text-ink-red-5"
							stroke-width="1.5"
						/>
						<span>{{ headline }}</span>
					</div>

					<!-- The whole message is in the tooltip, so the clamp costs
					     the reader nothing but a hover. -->
					<p
						v-if="detailHtml"
						class="line-clamp-2 px-4 text-p-xs text-ink-gray-5 [&_a]:underline"
						:title="detailText"
						v-html="detailHtml"
					></p>

					<Button
						class="shrink-0"
						variant="outline"
						:label="state === 'serverBusy' ? __('Try again') : __('Retry')"
						@click="chart.load(true)"
					>
						<template #prefix>
							<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</template>

			<template #empty>
				<template v-if="state === 'empty'">
					<p class="text-p-base text-ink-gray-5">{{ __('No data') }}</p>
					<Button
						v-if="props.filtered"
						variant="outline"
						:label="__('Reset filters')"
						@click="emit('resetFilters')"
					/>
				</template>

				<template v-else>
					<ChartSectionEmptySvg></ChartSectionEmptySvg>
					<p v-for="line in unconfigured" :key="line" class="text-ink-gray-4">
						{{ line }}
					</p>
				</template>
			</template>
		</ChartContainer>
	</div>
</template>
