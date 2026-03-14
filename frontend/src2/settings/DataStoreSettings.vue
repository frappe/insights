<script setup lang="ts">
import Checkbox from '../components/Checkbox.vue'
import SettingItem from './SettingItem.vue'
import useSettings from './settings'
import { __ } from '../translation'

const settings = useSettings()
settings.load()
</script>

<template>
	<div class="flex w-full flex-col gap-6 overflow-y-scroll p-8 px-10">
		<h1 class="text-xl font-semibold">{{ __('Data Store') }}</h1>

		<SettingItem
			:label="__('Enable')"
			:description="
				__(
					'Enable the data store to store database tables into a duckdb database for faster & cross-database queries.'
				)
			"
		>
			<Toggle v-model="settings.doc.enable_data_store" />
		</SettingItem>

		<SettingItem
			:label="__('Row Limit')"
			:description="
				__(
					'Set the maximum number of rows per table that will be imported into the data store. Default is 10,00,000'
				)
			"
		>
			<FormControl v-model="settings.doc.max_records_to_sync" class="w-28" type="number" />
		</SettingItem>

		<SettingItem
			:label="__('Memory Limit')"
			:description="
				__(
					'Set the maximum memory usage while importing tables into the data store. Default is 512MB'
				)
			"
		>
			<FormControl v-model="settings.doc.max_memory_usage" class="w-28" type="number" />
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
