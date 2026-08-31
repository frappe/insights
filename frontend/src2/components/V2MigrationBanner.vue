<script setup lang="ts">
import { call } from 'frappe-ui'
import { PackageOpen, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import session from '../session'
import { settingsTab, showSettingsDialog } from '../settings/settings'
import { __ } from '../translation'

const waiting = ref(0)
const canMigrate = ref(false)
const hidden = ref(false)
const hiding = ref(false)

// The server owns the rule - see `get_v2_migration_nudge`. This asks once and
// renders the answer.
if (session.user.is_admin) {
	call('insights.api.v2_migration.get_v2_migration_nudge').then((nudge: any) => {
		if (!nudge?.show) return
		waiting.value = nudge.waiting
		canMigrate.value = nudge.can_migrate
	})
}

const show = computed(() => !hidden.value && waiting.value > 0 && canMigrate.value)

function openMigration() {
	settingsTab.value = 'v2-migration'
	showSettingsDialog.value = true
}

// Hidden on the server, for the whole site: whoever decides v2 is done decides
// it for everyone, and should not be asked again on their next machine.
async function hide() {
	hiding.value = true
	try {
		await call('insights.api.v2_migration.hide_v2_migration_nudge')
		hidden.value = true
	} finally {
		hiding.value = false
	}
}
</script>

<template>
	<div v-if="show" class="flex flex-col gap-3 rounded-lg bg-white px-3 py-2.5 text-sm shadow-sm">
		<div class="flex items-start justify-between">
			<div class="flex flex-col gap-1">
				<div class="font-medium text-p-base text-ink-gray-8">
					{{ __('Move from v2') }}
				</div>
				<div class="text-p-xs text-ink-gray-6">
					{{
						waiting === 1
							? __('1 dashboard is still in Insights v2')
							: __('{0} dashboards are still in Insights v2', String(waiting))
					}}
				</div>
			</div>
			<button
				v-if="!hiding"
				class="mt-0.5 shrink-0 rounded p-0.5 text-ink-gray-5 hover:text-ink-gray-7"
				:title="__('Done with v2. Hide this.')"
				@click="hide"
			>
				<X class="h-3.5 w-3.5" />
			</button>
		</div>
		<Button :label="__('Review migration')" variant="subtle" @click="openMigration">
			<template #prefix>
				<PackageOpen class="h-3.5 w-3.5" />
			</template>
		</Button>
	</div>
</template>
