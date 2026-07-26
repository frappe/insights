<script setup lang="ts">
import { computed } from 'vue'
import { DateRangePicker } from 'frappe-ui'
import PresetWrapper from './PresetWrapper.vue'
import { getDatePresets, normalizeDateRange } from './filter_utils'

const dateRange = defineModel<string[]>()

const normalizedDateRange = computed({
	get: () => normalizeDateRange(dateRange.value),
	set: (val: any) => {
		dateRange.value = normalizeDateRange(val)
	},
})

const presets = getDatePresets('between')
</script>

<template>
	<div class="w-[18rem] select-none text-base flex flex-col gap-2">
		<PresetWrapper v-model="normalizedDateRange" :presets="presets">
			<DateRangePicker v-model="normalizedDateRange" class="w-full" />
		</PresetWrapper>
	</div>
</template>
