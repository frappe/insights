<script setup lang="ts">
import { __ } from '../translation'
import upgrade from './upgrade'
import UpgradeDetailsList from './UpgradeDetailsList.vue'

if (!upgrade.loaded) upgrade.load()
</script>

<template>
	<div class="flex w-full flex-col gap-6 overflow-y-scroll p-8 px-10">
		<div class="flex flex-col gap-1">
			<h1 class="text-2xl-semibold">{{ __('Upgrade details') }}</h1>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'Upgrade changes that rarely need anyone. Nothing here stops a dashboard you can see from working.',
					)
				}}
			</p>
		</div>
		<UpgradeDetailsList />
	</div>
</template>
