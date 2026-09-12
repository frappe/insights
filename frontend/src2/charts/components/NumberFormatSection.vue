<script setup lang="ts">
import type { NumberFormatConfig } from '../../types/chart.types'
import CollapsibleSection from './CollapsibleSection.vue'
import NumberFormatFields from './NumberFormatFields.vue'

// Every chart states its number format here, in its own section. The format is
// a property of the chart, so it belongs in the chart's form and not inside a
// Measure's settings popover.
const props = defineProps<{
	config: NumberFormatConfig
	/** See `NumberFormatFields`. Set it on a chart that draws one Measure. */
	soleMeasureName?: string
}>()
</script>

<template>
	<CollapsibleSection title="Number format" collapsed>
		<div class="flex flex-col gap-3 pt-1">
			<NumberFormatFields :config="props.config" :sole-measure-name="props.soleMeasureName" />
		</div>
	</CollapsibleSection>
</template>
