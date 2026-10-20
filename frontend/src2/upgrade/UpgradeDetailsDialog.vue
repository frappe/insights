<script setup lang="ts">
import { computed } from 'vue'
import { __ } from '../translation'
import upgrade from './upgrade'
import UpgradeDetailsList from './UpgradeDetailsList.vue'

const show = computed({
	get: () => upgrade.showDetails,
	set: (value: boolean) => (upgrade.showDetails = value),
})
</script>

<template>
	<Dialog
		v-model:open="show"
		size="2xl"
		:title="__('Details for admins')"
		:actions="[{ label: __('Close'), variant: 'solid', onClick: () => (show = false) }]"
	>
		<template #default>
			<div class="flex flex-col gap-4">
				<p class="text-p-base text-ink-gray-6">
					{{
						__(
							'Upgrade changes that rarely need anyone. Nothing here stops a dashboard you can see from working.',
						)
					}}
				</p>
				<UpgradeDetailsList class="max-h-[60vh] overflow-y-auto" />
			</div>
		</template>
	</Dialog>
</template>
