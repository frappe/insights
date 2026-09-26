<script setup lang="ts">
import { Button, LoadingIndicator } from 'frappe-ui'
import { ChartContainer } from 'frappe-ui/charts'
import { RefreshCcw } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue'
import { refusalDetail, refusalHeadline } from '../../not_permitted'
import { __ } from '../../translation'
import { emptyResult } from '../../query/helpers'
import {
	adaptChart,
	rendersOwnCards,
	type ChartFailure,
	type ChartStateProps,
	type DrillDownTarget,
} from '../adapter'
import type { ChartRead } from '../chart_view'
import { segmentClickEvents, type ChartSegmentClick, type ClickPoint } from '../drill/segment_click'
import { scopeText } from '../scoped_by'
import ChartSectionEmptySvg from './ChartSectionEmptySvg.vue'
import ScopeMark from './ScopeMark.vue'
import ChartStateMessage from './ChartStateMessage.vue'

// The chart itself: the type it is, the data it has, and every state in between.
// One state machine — a surface that renders a chart renders this, and gets the
// failure, the reload and the empty result along with the chart. Segment
// clicks are reported, never handled — a drill is a dialog the caller shows,
// so it is the caller that owns it.
//
// It renders no card. The border, the padding and the title belong to whoever
// renders the chrome, and `#actions` reaches the row the title heads, in every
// state and through every filler: `ChartChrome` on an Insights page, the island's chrome on
// a desk workspace. A host that has one mounts this and gets the chart alone.
//
// The states are frappe-ui's, and what goes inside them is the adapter's answer:
// it says which component renders this Chart and what to hand it, so nothing here
// switches on chart type. A new type is added in `charts/adapter`, not here.
//
// Where the states are rendered is the one thing that varies, and the adapter
// answers that too. A type with no card of its own gets the states rendered around
// the plot. A type that renders cards — a Number Chart's readings are cards
// already — renders them inside each card, so it is mounted in every state and
// handed `ChartStateProps` instead.
//
// `readonly` is for a surface that cannot change the chart. A surface may say
// so, and a chart the reader may not edit is read-only wherever it is rendered —
// read off the document, so no host has to remember to pass it. It decides two
// things, and they are the same thing: a table's sort rewrites the chart's config
// and re-runs its query, which a reader holds neither half of, so the control is
// not shown rather than shown and dead — and for the same reason a reader is
// told about the data ("No data") where an author is told about the config.
const props = defineProps<{
	chart: ChartRead
	// heads the chart. Left out, no title is shown anywhere in it — which is what
	// a host that prints its own asks for.
	title?: string
	// which reading to show, for a Number Chart. A host that shows one reading per
	// cell says which. One that renders the chart says nothing and gets them all.
	reading?: string
	readonly?: boolean
	// whether filters narrowed the rows, so an empty card can show a way to clear them.
	// Only a surface that owns filter state can say, and only it can reset them.
	filtered?: boolean
}>()
const emit = defineEmits<{
	// where the reader pointed, for a surface that shows the drill menu
	segmentClick: [click: ChartSegmentClick]
	resetFilters: []
}>()

const readonly = computed(() => props.readonly || props.chart.doc.can_write === false)

const chart_type = computed(() => props.chart.doc.chart_type)
const config = computed(() => props.chart.doc.config)
const result = computed(() => props.chart.result || emptyResult())

// Whether the filler renders the states itself. A property of the chart type, so
// it is settled before there is a result to adapt.
const ownsStates = computed(() => rendersOwnCards(chart_type.value))

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
		comparisonRows: props.chart.comparisonRows,
		title: props.title,
		reading: props.reading,
		readonly: readonly.value,
		drillable: props.chart.drillable,
		executing: props.chart.executing,
		page: props.chart.goToPage
			? {
					current: props.chart.currentPage,
					size: props.chart.pageSize,
					totalRowCount: result.value.totalRowCount || undefined,
					goTo: props.chart.goToPage,
					fetchCount: props.chart.fetchResultCount,
			  }
			: undefined,
		download:
			props.chart.exportResults && props.chart.cancelDownload
				? {
						downloading: props.chart.downloading,
						exportResults: props.chart.exportResults,
						cancelDownload: props.chart.cancelDownload,
				  }
				: undefined,
	})
})

// Rows on screen stay through the next run, veiled. Blanking them unmounts the
// plot, and a plot mounted again is a new echarts instance that replays its
// entry animation — frappe-ui holds that back only for an instance that has
// rendered once. The builder re-runs on every edit, so a color tweak would grow
// the plot from nothing.
//
// The veil waits: a run the server answers from cache is over before a veil can
// be read, and one that flashes on every edit is its own flicker.
const hasRows = computed(() => Boolean(result.value.rows?.length))
const reloading = computed(() => props.chart.executing && hasRows.value)
const VEIL_DELAY_MS = 300
const veiled = ref(false)
let veilTimer: ReturnType<typeof setTimeout> | undefined
watch(reloading, (running) => {
	clearTimeout(veilTimer)
	if (running) veilTimer = setTimeout(() => (veiled.value = true), VEIL_DELAY_MS)
	else veiled.value = false
})
// a card unmounted mid-reload leaves a timer that writes to a component that is
// no longer there
onBeforeUnmount(() => clearTimeout(veilTimer))

// What the card shows, in the order the store settles it: a failure outranks the
// reload that would replace it, and a reload outranks the rows it is replacing.
// `unconfigured` is a new chart's state and the state a config the
// server refused puts it back in — nothing is rendered, and the space the chart
// would take is where the reason is printed.
const state = computed(() => {
	if (props.chart.failed) return props.chart.serverBusy ? 'serverBusy' : 'failed'
	if (props.chart.executing && !hasRows.value) return 'loading'
	// nothing ran, so config errors and an empty result do not apply
	if (props.chart.notPermitted) return 'notPermitted'
	if (props.chart.configErrors.length) return 'unconfigured'
	if (props.chart.empty) return 'empty'
	return filler.value ? 'chart' : 'unconfigured'
})

// What an author has left to fill in, printed where the chart would be. It is
// the same line a chart nobody has configured yet shows, so a half-configured
// chart says what is missing rather than repeating the prompt to configure it. A reader owns
// no config, so they are never told about one.
const unconfigured = computed(() => {
	const errors = props.chart.configErrors
	// a reader has no chart type to pick and no options to configure, so they are
	// told what there is instead of what to do about it
	if (readonly.value) return [__('This chart cannot be rendered')]
	if (!errors.length) {
		return [__('Pick a chart type and configure options to see the chart here')]
	}
	return errors
})

// Any non-empty string puts `ChartContainer` in its error state. The slot below
// renders the block itself, because a retry belongs beside the message.
//
// The headline names what happened and the detail names why. They are two lines
// and not one because a card can be short enough to hold only one of them, and
// then the line to keep is the one every reader can act on. The detail is what
// gives way, in this block and in a card that renders the failure itself.
//
// The headline is short enough for the narrowest surface that renders it, which is
// one reading of a Number Chart. One line for both, rather than a second string
// that says the same thing in fewer words.
const headline = computed(() => {
	if (state.value === 'serverBusy') return __('The server is busy')
	if (state.value === 'failed') return __('Could not load')
	// Frappe's term. It is a card state like No data and Could not load, not a
	// layout of its own, so every state reads the same way.
	if (state.value === 'notPermitted') return refusalHeadline()
	return null
})

// What the server said. An author can act on it. A reader owns neither the query
// nor the config it names, so a reader gets the headline alone.
//
// A refusal is the exception. Authors and readers both get the doctypes it
// names: neither of them owns the permission, and the doctype is the name the
// site's permission settings use.
const detail = computed(() => {
	if (state.value === 'notPermitted') {
		return refusalDetail(
			props.chart.notPermitted,
			__('You do not have access to the data behind this chart'),
		)
	}
	if (state.value !== 'failed' || readonly.value) return ''
	return props.chart.failure
})

const failure = computed<ChartFailure | null>(() =>
	headline.value
		? {
				...(state.value === 'notPermitted' ? { kind: 'notPermitted' as const } : {}),
				headline: headline.value,
				detailText: detail.value || undefined,
		  }
		: null,
)

// What a filler that owns its states is told, bound as props beside the rest of
// its input. Nothing here knows which component reads them.
const stateProps = computed(() => {
	if (!ownsStates.value) return {}
	const owned: ChartStateProps = {
		loading: state.value === 'loading',
		failure: failure.value,
		empty: state.value === 'empty',
		onRetry: () => props.chart.load(true),
	}
	return owned
})

// The events a filler reports a click through, bound without knowing which chart
// type emits which. The adapter names them and turns each payload into the point
// behind it.
//
// A source without drill support gets no click handlers: the dialog would open
// on a click the server refuses, and show a retry that can never succeed. Gated
// here rather than in each adapter, because the source decides whether a drill is
// possible, and every chart type reports its clicks through this one map.
const fillerEvents = computed(() =>
	props.chart.drillable === false
		? {}
		: segmentClickEvents(filler.value, result.value.columns, reportSegment),
)

// Tells the reader that their own permissions narrowed the rows, so a partial
// number is not read as the total. Only User Permission records are named. A
// role's match condition also narrows the rows, but there is no document to
// name. A team's Table Restriction is also shown without names.
//
// It is a mark after the title, not a line in the card. The author sized the
// card, and a line under the plot would take space from it. It belongs to the
// title, so it goes in `#title-suffix`, not in `#actions` at the end of the row.
const scope = computed(() => scopeText(props.chart.scopedBy, props.chart.narrowedByPermissions))

// echarts hands over the point, not the event, so the capture phase records
// the click position before the chart's own handler runs.
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
	<div class="relative h-full w-full" data-testid="chart" @click.capture="rememberPoint">
		<component
			v-if="filler && (state === 'chart' || ownsStates)"
			:is="filler.component"
			v-bind="{ ...filler.props, ...stateProps }"
			v-on="fillerEvents"
		>
			<template v-if="scope" #title-suffix>
				<ScopeMark
					:applied="props.chart.scopedBy"
					:narrowed="props.chart.narrowedByPermissions"
				/>
			</template>

			<template v-if="$slots.actions" #actions>
				<slot name="actions" />
			</template>
		</component>

		<!-- Every state but the chart. `#loading` is left alone: v2 renders a
		     skeleton the size of the plot, which is what a chart still filling in
		     should read as to a reader and to an author alike. -->
		<ChartContainer
			v-else
			:title="props.title"
			:loading="state === 'loading'"
			:error="headline"
			:empty="true"
		>
			<template v-if="scope" #title-suffix>
				<ScopeMark
					:applied="props.chart.scopedBy"
					:narrowed="props.chart.narrowedByPermissions"
				/>
			</template>

			<!-- The acts stay put through every state: a chart that failed is a
			     chart to run again. -->
			<template v-if="$slots.actions" #actions>
				<slot name="actions" />
			</template>

			<template #error>
				<!-- centred, because this block takes the plot's place -->
				<ChartStateMessage
					v-if="failure"
					class="w-full items-center text-center"
					:failure="failure"
					detailed
				>
					<!-- the queue turns a card away rather than queueing it, so
					     asking again is the whole remedy — and a chart that failed
					     for any other reason is worth one more try too. A refusal
					     gets no retry: the reader cannot change their own
					     permissions. -->
					<Button
						v-if="state !== 'notPermitted'"
						class="shrink-0"
						variant="outline"
						:label="state === 'serverBusy' ? __('Try again') : __('Retry')"
						@click="chart.load(true)"
					>
						<template #prefix>
							<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
				</ChartStateMessage>
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

		<!-- The data table's veil, over the whole card: the body does not know
		     where a filler keeps its plot. -->
		<div
			v-if="veiled"
			class="absolute inset-0 flex items-center justify-center rounded-4 bg-surface-base/30 backdrop-blur-sm"
			role="status"
		>
			<span class="sr-only">{{ __('Loading chart') }}</span>
			<LoadingIndicator class="h-5 w-5 text-ink-gray-4" />
		</div>
	</div>
</template>
