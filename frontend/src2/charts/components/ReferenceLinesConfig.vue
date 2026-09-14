<script setup lang="ts">
import AddSlotButton from './AddSlotButton.vue'
import { Settings, X as XIcon } from 'lucide-vue-next'
import { computed } from 'vue'
import { getUniqueId } from '../../helpers'
import { __ } from '../../translation'
import ColorInput from '../../components/ColorInput.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import {
	AxisChartConfig,
	ReferenceAggregate,
	ReferenceLabelPlacement,
	ReferenceLine,
} from '../../types/chart.types'
import CollapsibleSection from './CollapsibleSection.vue'
import NumberInput from '../../components/NumberInput.vue'

// The whole Chart config, not the axis alone: a line reads any Measure the
// Chart carries, and the tooltip Measures do not live on the axis.
const config = defineModel<AxisChartConfig>({ required: true })
const y_axis = computed(() => config.value.y_axis)

const lines = computed(() => y_axis.value.reference_lines || [])

// A computed line reads one of the Chart's own Measures. The result carries no
// other numbers, so a Measure from anywhere else would have nowhere to sit.
// A tooltip Measure is one of them: it is not drawn, but it is measured, and a
// target on the tooltip is exactly the kind a rule is computed from.
const measureOptions = computed(() =>
	[
		...(y_axis.value.series || []).map((series) => series.measure?.measure_name),
		...(config.value.tooltip?.measures || []).map((measure) => measure?.measure_name),
	].filter((name): name is string => Boolean(name)),
)

// Named as an end of the rule and a side of it. A rule drawn down the plot
// carries its label rotated, so its sides read as the left and the right of it.
const labelPlacementOptions: { label: string; value: ReferenceLabelPlacement }[] = [
	{ label: __('End, above'), value: 'end-top' },
	{ label: __('End, below'), value: 'end-bottom' },
	{ label: __('Start, above'), value: 'start-top' },
	{ label: __('Start, below'), value: 'start-bottom' },
]

const atOptions: { label: string; value: ReferenceAggregate | '' }[] = [
	{ label: __('Constant'), value: '' },
	{ label: __('Average'), value: 'average' },
	{ label: __('Median'), value: 'median' },
	{ label: __('Min'), value: 'min' },
	{ label: __('Max'), value: 'max' },
	{ label: __('Sum'), value: 'sum' },
]

function addReferenceLine() {
	if (!y_axis.value.reference_lines) {
		y_axis.value.reference_lines = []
	}
	y_axis.value.reference_lines.push({ id: getUniqueId(), axis: 'y' })
}

function removeReferenceLine(index: number) {
	y_axis.value.reference_lines?.splice(index, 1)
}

// A line sits at one thing, so switching kind drops what the other kind held.
function setAggregate(line: ReferenceLine, aggregate: ReferenceAggregate | '') {
	if (!aggregate) {
		delete line.aggregate
		delete line.measure_name
		return
	}
	delete line.value
	line.aggregate = aggregate
	// An aggregate is a number, so it is read on a value axis and nowhere else.
	line.axis = 'y'
	// A chart that names no Measure yet leaves the picker empty rather than
	// writing `undefined` into the config as the Measure this line reads.
	const first = measureOptions.value[0]
	if (!line.measure_name && first) line.measure_name = first
}
</script>

<template>
	<CollapsibleSection :title="__('Reference Lines')">
		<div class="flex flex-col gap-1.5 pt-1">
			<div v-for="(line, index) in lines" :key="line.id" class="flex items-end gap-1">
				<!-- What the line sits at leads the row, so the list says what each
				line is without opening anything. -->
				<div class="w-[6.5rem] flex-shrink-0">
					<FormControl
						type="select"
						:options="atOptions"
						:model-value="line.aggregate || ''"
						@update:model-value="setAggregate(line, $event)"
					/>
				</div>
				<div class="min-w-0 flex-1">
					<FormControl
						v-if="line.aggregate"
						type="select"
						v-model="line.measure_name"
						:options="measureOptions"
					/>
					<FormControl
						v-else-if="line.axis === 'x'"
						type="text"
						v-model="line.value"
						:placeholder="__('e.g. Jan')"
					/>
					<NumberInput
						v-else
						:model-value="line.value as number | undefined"
						@update:model-value="line.value = $event"
						:placeholder="__('e.g. 60')"
					/>
				</div>
				<Popover side="bottom" align="end">
					<template #trigger>
						<Button>
							<template #icon>
								<Settings class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
							</template>
						</Button>
					</template>
					<template #default>
						<div class="flex w-[14rem] flex-col gap-2 p-2">
							<InlineFormControlLabel v-if="!line.aggregate" :label="__('Axis')">
								<FormControl
									type="select"
									v-model="line.axis"
									:options="[
										{ label: __('Y (horizontal)'), value: 'y' },
										{ label: __('X (vertical)'), value: 'x' },
									]"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel
								v-if="(line.axis || 'y') === 'y'"
								:label="__('Align')"
							>
								<FormControl
									type="select"
									v-model="line.align"
									:options="[
										{ label: __('Left'), value: 'Left' },
										{ label: __('Right'), value: 'Right' },
									]"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel :label="__('Label')">
								<FormControl
									type="text"
									v-model="line.label"
									:placeholder="line.aggregate ? __('Auto') : __('e.g. Target')"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel :label="__('Label at')">
								<FormControl
									type="select"
									v-model="line.label_placement"
									:options="labelPlacementOptions"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel :label="__('Color')">
								<ColorInput
									:model-value="line.color"
									@update:model-value="line.color = $event"
									placement="left-start"
								/>
							</InlineFormControlLabel>
							<Toggle :label="__('Dashed')" v-model="line.dashed" />
						</div>
					</template>
				</Popover>
				<Button @click="removeReferenceLine(index)">
					<template #icon>
						<XIcon class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
			</div>
		</div>
		<AddSlotButton :label="__('Add reference line')" @click="addReferenceLine" />
	</CollapsibleSection>
</template>
