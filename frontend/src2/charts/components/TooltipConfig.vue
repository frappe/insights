<script setup lang="ts">
import { computed } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import { copy } from '../../helpers'
import { AxisChartConfig } from '../../types/chart.types'
import { ColumnOption, MeasureOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import MeasurePicker from './MeasurePicker.vue'
import NumberFormatFields from './NumberFormatFields.vue'

const props = defineProps<{ columnOptions: ColumnOption[] }>()

// The whole Chart config, not the `tooltip` key alone: the section owns the
// rule that a split takes it away, and reading `split_by` from here keeps that
// rule in one place rather than in every form that draws the section.
const config = defineModel<AxisChartConfig>({ required: true })

// A split turns every Measure into one column per split value, which is a
// value per mark. A tooltip extra is one value per category, so the two shapes
// do not meet — the section goes away rather than letting an author write a
// config the chart would ignore.
const splitBy = computed(() => Boolean(config.value.split_by?.dimension?.column_name))

// Written on the first add, never on mount: seeding it here would be one
// autosave and two re-runs of the chart data for opening a chart.
const measures = computed({
	get: () => config.value.tooltip?.measures || [],
	set: (value) => {
		config.value.tooltip = { measures: value }
	},
})

function addMeasure() {
	if (!config.value.tooltip) config.value.tooltip = { measures: [] }
	config.value.tooltip.measures.push(copy({} as MeasureOption))
}
</script>

<template>
	<!-- Under a split the section is gone. It stays only to say where measures
	the author already picked went: dropping them without a word reads as a bug,
	and they come back the moment the split does. -->
	<CollapsibleSection v-if="!splitBy || measures.length" title="Tooltip" collapsed>
		<p v-if="splitBy" class="pt-1 text-xs text-ink-gray-5">
			A split draws one series per split value, so these
			{{ measures.length }} measures are off the tooltip until it is cleared.
		</p>
		<div v-else class="pt-1">
			<p class="mb-1.5 text-xs text-ink-gray-5">
				Measures printed in the tooltip only, never drawn.
			</p>
			<DraggableList v-model:items="measures" group="tooltip-measures">
				<template #item="{ item, index }">
					<MeasurePicker
						:model-value="item"
						:column-options="props.columnOptions"
						@update:model-value="Object.assign(item, $event || {})"
						@remove="measures.splice(index, 1)"
					>
						<template #config-fields>
							<NumberFormatFields
								:config="config"
								:measure-name="item?.measure_name"
							/>
						</template>
					</MeasurePicker>
				</template>
			</DraggableList>
			<button
				class="mt-1.5 text-left text-xs text-ink-gray-5 hover:underline"
				@click="addMeasure"
			>
				+ Add measure
			</button>
		</div>
	</CollapsibleSection>
</template>
