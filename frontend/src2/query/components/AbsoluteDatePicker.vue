<script setup lang="ts">
import { DateRangePicker } from 'frappe-ui'
import PresetWrapper from './PresetWrapper.vue'
import { getDatePresets } from './filter_utils'

const dateRange = defineModel<string[]>()

const presets = getDatePresets('between')
</script>

<template>
	<div class="w-[18rem] select-none text-base flex flex-col gap-2">
		<PresetWrapper v-model="dateRange" :presets="presets">
			<DateRangePicker v-model="dateRange" class="w-full" />
		</PresetWrapper>
	</div>
</template>
