<script setup lang="ts">
import { Button } from 'frappe-ui'
import { ChartCard, ChartContainer } from 'frappe-ui/charts'
import { AlertTriangle, RefreshCcw } from 'lucide-vue-next'
import { computed, shallowRef, watch } from 'vue'
import { __ } from '../../translation'
import { EMPTY_RESULT } from '../../query/helpers'
import { adaptChart, type DrillDownTarget } from '../adapter'
import { ChartRead } from '../chart_read'
import { segmentClickEvents, type ChartSegmentClick, type ClickPoint } from '../drill/segment_click'
import ChartSectionEmptySvg from './ChartSectionEmptySvg.vue'

// The chart itself: the type it is, the data it has, and every state in between.
// One card, one state machine — a surface that draws a chart card draws this,
// and gets the failure, the reload and the empty result along with the picture.
// Segment clicks are reported, never handled — drill-down is a dialog the caller
// offers, so it is the caller that carries it.
//
// The card and the states are frappe-ui's, for every chart type without
// exception. What goes inside them is the adapter's answer: it says which
// component draws this Chart and what to hand it, so nothing here switches on
// chart type. A new type is added in `charts/adapter`, not here.
//
// `readonly` is for a surface that cannot change the chart. It decides two
// things, and they are the same thing: a table's sort rewrites the chart's config
// and re-runs its query, which a reader holds neither half of, so the control is
// not offered rather than offered and dead — and for the same reason a reader is
// told about the data ("No data") where an author is told about the config.
const props = defineProps<{
	chart: ChartRead
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

const adapted = computed(() => {
	// the result outlives a chart type switch, so without this the adapter would
	// run against the incoming type's still-empty config
	if (props.chart.configErrors.length) return
	if (!result.value.columns?.length) return
	return adaptChart({
		chart_type: chart_type.value,
		config: config.value,
		result: result.value,
		title: props.chart.doc.title,
		readonly: props.readonly,
		executing: props.chart.executing,
	})
})

// The store holds on to the rows when the server answers with config errors, so
// the card goes on showing what it last drew while a slot is being filled — the
// adapter cannot run against a config the server refused, but its last output is
// still a true picture of those rows. A type switch is not that case: the
// picture belongs to the type that drew it.
type Drawn = { chart_type: string; filler: NonNullable<ReturnType<typeof adaptChart>> }
const lastDrawn = shallowRef<Drawn>()
watch(adapted, (filler) => {
	if (filler) lastDrawn.value = { chart_type: chart_type.value, filler }
})

const filler = computed(() => {
	if (!props.chart.configErrors.length) return adapted.value
	return lastDrawn.value?.chart_type === chart_type.value ? lastDrawn.value.filler : undefined
})

// A table that already has rows keeps them while the next run is in flight.
// Every other type blanks, so this is a restoration and not a rule: a table on a
// filtered dashboard would otherwise blank on every filter move, which reads as
// the card breaking rather than the card catching up. The rule the exception
// wants — every type holding its last picture while it reloads — is a bigger
// change than this one, and belongs with the one the config errors already make.
const keepsLastPicture = computed(
	() => chart_type.value === 'Table' && Boolean(result.value.rows?.length),
)

// What the card shows, in the order the store settles it: a failure outranks the
// reload that would replace it, and a reload outranks the rows it is replacing.
// `unconfigured` is the state a chart is born in — nothing has been drawn yet and
// nothing is on its way.
const state = computed(() => {
	if (props.chart.failed) return props.chart.serverBusy ? 'serverBusy' : 'failed'
	if (props.chart.executing && !keepsLastPicture.value) return 'loading'
	if (props.chart.empty) return 'empty'
	return filler.value ? 'chart' : 'unconfigured'
})

// Any non-empty string puts the container in its error state. The slot below
// draws the message itself, because a retry belongs beside it.
const failure = computed(() => {
	if (state.value === 'serverBusy') return __('The server is busy')
	if (state.value === 'failed') return __('This chart is not available')
	return null
})

// A filler that draws cards of its own is left to draw them. Only the picture is
// asked: a loading, empty or failed card is chrome, and chrome is the same for
// every type.
const drawCard = computed(() => state.value !== 'chart' || filler.value?.card !== false)

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
	<div class="flex h-full w-full flex-col" @click.capture="rememberPoint">
		<!-- the errors name slots in the config, so only a surface that can fill
		     them has any use for them. It sits above the picture rather than in
		     place of it, because the picture under it is still the last one the
		     server accepted. -->
		<div
			v-if="!props.readonly && chart.configErrors.length"
			class="flex flex-shrink-0 flex-col gap-0.5 rounded-t-4 border border-b-0 border-outline-gray-2 bg-surface-amber-1 px-3 py-1.5"
		>
			<p v-for="error in chart.configErrors" :key="error" class="text-p-sm text-ink-amber-2">
				{{ error }}
			</p>
		</div>

		<div class="min-h-0 w-full flex-1">
			<ChartCard class="h-full" :card="drawCard">
				<component
					v-if="state === 'chart' && filler"
					:is="filler.component"
					v-bind="filler.props"
					v-on="fillerEvents"
				/>

				<!-- Every state but the picture. `#loading` is left alone: v2 draws a
				     skeleton the size of the plot, which is what a card still filling
				     in should read as to a reader and to an author alike. -->
				<ChartContainer
					v-else
					:title="chart.doc.title"
					:loading="state === 'loading'"
					:error="failure"
					:empty="true"
				>
					<!-- the queue turns a card away rather than queueing it, so asking
					     again is the whole remedy — and a chart that failed for any
					     other reason is worth one more try too -->
					<template #error>
						<AlertTriangle
							v-if="state === 'failed'"
							class="h-6 w-6 text-ink-gray-4"
							stroke-width="1"
						/>
						<p class="text-p-base text-ink-gray-5">{{ failure }}</p>
						<Button
							variant="outline"
							:label="state === 'serverBusy' ? __('Try again') : __('Retry')"
							@click="chart.load(true)"
						>
							<template #prefix>
								<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
							</template>
						</Button>
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
							<p class="text-ink-gray-4">
								{{
									__(
										'Pick a chart type and configure options to see the chart here',
									)
								}}
							</p>
						</template>
					</template>
				</ChartContainer>
			</ChartCard>
		</div>
	</div>
</template>
