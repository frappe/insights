<script setup lang="ts">
import { useRouter } from 'vue-router'
import { __ } from '../translation'
import { showSettingsDialog } from './settings'

const router = useRouter()

// The migration is a page of its own, so this tab only points at it - and has to
// close the dialog it lives in, or the page opens behind it.
function openMigration() {
	showSettingsDialog.value = false
	router.push('/migration')
}
</script>

<template>
	<div class="flex h-full w-full flex-col gap-3 p-8 px-10">
		<h1 class="text-xl font-semibold">{{ __('Migrate from v2') }}</h1>
		<p class="text-p-sm text-ink-gray-6">
			{{
				__(
					'Copy your Insights v2 dashboards into v3 workbooks. Your v2 dashboards stay untouched.',
				)
			}}
		</p>
		<Button
			class="self-start"
			variant="solid"
			:label="__('Open the migration page')"
			@click="openMigration"
		/>
	</div>
</template>
