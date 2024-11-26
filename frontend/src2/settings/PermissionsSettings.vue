<script setup lang="ts">
import Checkbox from '../components/Checkbox.vue'
import SettingItem from './SettingItem.vue'
import useSettings from './settings'

const settings = useSettings()
settings.load()
</script>

<template>
	<div class="flex w-full flex-col gap-6 overflow-y-scroll p-8 px-10">
		<h1 class="text-xl font-semibold">Permission</h1>

		<SettingItem
			label="Enable Permissions"
			description="When disabled, all users will have access to all data sources and tables."
		>
			<Checkbox v-model="settings.doc.enable_permissions" />
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
