<script setup lang="ts">
import { Settings, X as XIcon } from 'lucide-vue-next'
import { computed } from 'vue'
import ColorInput from '../../components/ColorInput.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig, ReferenceAggregate, ReferenceLine } from '../../types/chart.types'
import CollapsibleSection from './CollapsibleSection.vue'

const y_axis = defineModel<AxisChartConfig['y_axis']>({ required: true })

const lines = computed(() => y_axis.value.reference_lines || [])

// A computed line reads one of the Chart's own Measures. The result carries no
// other numbers, so a Measure from anywhere else would have nowhere to sit.
const measureOptions = computed(() =>
	(y_axis.value.series || [])
		.map((series) => series.measure?.measure_name)
		.filter((name): name is string => Boolean(name)),
)

const atOptions: { label: string; value: ReferenceAggregate | '' }[] = [
	{ label: 'Constant', value: '' },
	{ label: 'Average', value: 'average' },
	{ label: 'Median', value: 'median' },
	{ label: 'Min', value: 'min' },
	{ label: 'Max', value: 'max' },
	{ label: 'Sum', value: 'sum' },
]

function addReferenceLine() {
	if (!y_axis.value.reference_lines) {
		y_axis.value.reference_lines = []
	}
	y_axis.value.reference_lines.push({ axis: 'y' })
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
	line.measure_name = line.measure_name || measureOptions.value[0]
}
</script>

<template>
	<CollapsibleSection title="Reference Lines">
		<div class="flex flex-col gap-1.5 pt-1">
			<div v-for="(line, index) in lines" :key="index" class="flex items-end gap-1">
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
				<div class="flex-1 overflow-hidden">
					<FormControl
						v-if="line.aggregate"
						type="select"
						v-model="line.measure_name"
						:options="measureOptions"
					/>
					<FormControl
						v-else
						:type="line.axis === 'x' ? 'text' : 'number'"
						v-model="line.value"
						:placeholder="line.axis === 'x' ? 'e.g. Jan' : 'e.g. 60'"
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
							<InlineFormControlLabel v-if="!line.aggregate" label="Axis">
								<FormControl
									type="select"
									v-model="line.axis"
									:options="[
										{ label: 'Y (horizontal)', value: 'y' },
										{ label: 'X (vertical)', value: 'x' },
									]"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel v-if="(line.axis || 'y') === 'y'" label="Align">
								<FormControl
									type="select"
									v-model="line.align"
									:options="['Left', 'Right']"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel label="Label">
								<FormControl
									type="text"
									v-model="line.label"
									:placeholder="line.aggregate ? 'Auto' : 'e.g. Target'"
								/>
							</InlineFormControlLabel>
							<InlineFormControlLabel label="Color">
								<ColorInput
									:model-value="line.color"
									@update:model-value="line.color = $event"
									placement="left-start"
								/>
							</InlineFormControlLabel>
							<Toggle label="Dashed" v-model="line.dashed" />
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
		<button
			class="mt-1.5 text-left text-xs text-ink-gray-5 hover:underline"
			@click="addReferenceLine"
		>
			+ Add reference line
		</button>
	</CollapsibleSection>
</template>
