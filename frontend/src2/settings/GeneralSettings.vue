<script setup lang="ts">
import Checkbox from '../components/Checkbox.vue'
import DatePickerControl from '../query/components/DatePickerControl.vue'
import SettingItem from './SettingItem.vue'
import useSettings from './settings'

const settings = useSettings()
settings.load()
</script>

<template>
	<div class="flex w-full flex-col gap-6 overflow-y-scroll p-8 px-10">
		<h1 class="text-xl font-semibold">General</h1>
		<SettingItem
			label="Logo"
			description="Appears in the top left corner of the application and in the browser tab next to the page title. Recommended size: 32x32px in PNG format."
		>
			<div class="flex h-full w-full items-center justify-center rounded border">
				<img src="../assets/insights-logo-new.svg" alt="Logo" class="w-8 rounded" />
			</div>
		</SettingItem>

		<SettingItem
			label="Fiscal Year Start"
			description="Set the start of the fiscal year for the organization. This will be used to calculate
					quarterly and yearly data."
		>
			<DatePickerControl
				class="w-28"
				placeholder="Select Date"
				:model-value="[settings.doc.fiscal_year_start]"
				@update:model-value="settings.doc.fiscal_year_start = $event?.[0] || '2024-04-01'"
			/>
		</SettingItem>

		<SettingItem
			label="Week Starts On"
			description="Set the start of the week for the organization. This will be used to calculate weekly data."
		>
			<FormControl
				class="w-28"
				type="select"
				v-model="settings.doc.week_starts_on"
				:options="[
					'Sunday',
					'Monday',
					'Tuesday',
					'Wednesday',
					'Thursday',
					'Friday',
					'Saturday',
				]"
			/>
		</SettingItem>

		<div class="flex justify-end">
			<Button
				label="Update"
				variant="solid"
				:disabled="!settings.isdirty"
				:loading="settings.saving"
				@click="() => settings.save()"
			/>
		</div>
	</div>
</template>
