<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { call } from 'frappe-ui'
import { PackageOpen, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import session from '../session'
import { settingsTab, showSettingsDialog } from '../settings/settings'
import { __ } from '../translation'

const props = defineProps<{ workbookCount: number }>()

// Once a site has workbooks of its own, the v2 dashboards are no longer the
// thing to do next, so the callout stops asking.
const FEW_WORKBOOKS = 3

const dismissed = useStorage('insights:v2-migration-callout-dismissed', false)
const waiting = ref(0)

// The count endpoint answers 0 on a site that never had v2, so nothing here has
// to know whether the doctype exists.
if (session.user.is_admin) {
	call('insights.api.v2_migration.count_v2_dashboards').then((counts: any) => {
		waiting.value = Math.max((counts?.total || 0) - (counts?.migrated || 0), 0)
	})
}

const show = computed(
	() => !dismissed.value && waiting.value > 0 && props.workbookCount < FEW_WORKBOOKS,
)

function openMigration() {
	settingsTab.value = 'v2-migration'
	showSettingsDialog.value = true
}
</script>

<template>
	<div
		v-if="show"
		class="flex items-center justify-between gap-3 rounded border border-outline-gray-2 bg-surface-gray-1 px-4 py-3"
	>
		<div class="flex items-center gap-3">
			<PackageOpen class="h-5 w-5 shrink-0 text-ink-gray-6" />
			<span class="text-p-base text-ink-gray-8">
				{{
					waiting === 1
						? __('You have 1 dashboard in Insights v2. Bring it over.')
						: __(
								'You have {0} dashboards in Insights v2. Bring them over.',
								String(waiting),
						  )
				}}
			</span>
		</div>
		<div class="flex items-center gap-2">
			<Button variant="subtle" :label="__('Migrate from v2')" @click="openMigration" />
			<Button variant="ghost" :tooltip="__('Dismiss')" @click="dismissed = true">
				<template #icon>
					<X class="h-4 w-4" />
				</template>
			</Button>
		</div>
	</div>
</template>
