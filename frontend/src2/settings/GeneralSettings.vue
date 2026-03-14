<script setup lang="ts">
import { call } from 'frappe-ui'
import { ref } from 'vue'
import { createToast } from '../helpers/toasts'
import DatePickerControl from '../query/components/DatePickerControl.vue'
import session from '../session'
import SettingItem from './SettingItem.vue'
import useSettings from './settings'

const settings = useSettings()
settings.load()

const demoLoading = ref(false)

async function setupDemoData() {
	demoLoading.value = true
	try {
		await call('insights.setup.setup_wizard.setup_demo_data')
		session.user.has_demo_data = true
		createToast({
			title: __('Demo Data Ready'),
			message: __('Sample data and workbook have been set up successfully'),
			variant: 'success',
		})
	} catch {
		createToast({
			title: __('Setup Failed'),
			message: __('Failed to setup demo data'),
			variant: 'error',
		})
	} finally {
		demoLoading.value = false
	}
}
</script>

<template>
	<div class="flex w-full flex-col gap-6 overflow-y-scroll p-8 px-10">
		<h1 class="text-xl font-semibold">{{ __('General') }}</h1>
		<SettingItem
			:label="__('Logo')"
			:description="__('Appears in the top left corner of the application and in the browser tab next to the page title. Recommended size: 32x32px in PNG format.')"
		>
			<div class="flex h-full w-full items-center justify-center rounded border">
				<img src="../assets/insights-logo-new.svg" alt="Logo" class="w-8 rounded" />
			</div>
		</SettingItem>

		<SettingItem
			:label="__('Fiscal Year Start')"
			:description="__('Set the start of the fiscal year for the organization. This will be used to calculate quarterly and yearly data.')"
		>
			<DatePickerControl
				class="w-28"
				:placeholder="__('Select Date')"
				:model-value="[settings.doc.fiscal_year_start]"
				@update:model-value="settings.doc.fiscal_year_start = $event?.[0] || '2024-04-01'"
			/>
		</SettingItem>

		<SettingItem
			:label="__('Week Starts On')"
			:description="__('Set the start of the week for the organization. This will be used to calculate weekly data.')"
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

		<SettingItem
			v-if="session.user.is_admin && !session.user.has_demo_data"
			:label="__('Demo Data')"
			:description="__('Set up sample data and a pre-built workbook to explore Insights features.')"
		>
			<Button
				variant="subtle"
				size="sm"
				:label="__('Setup Demo Data')"
				:loading="demoLoading"
				@click="setupDemoData"
			/>
		</SettingItem>

		<div class="flex justify-end">
			<Button
				:label="__('Update')"
				variant="solid"
				:disabled="!settings.isdirty"
				:loading="settings.saving"
				@click="() => settings.save()"
			/>
		</div>
	</div>
</template>
