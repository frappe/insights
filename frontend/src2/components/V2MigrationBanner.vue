<script setup lang="ts">
import { PackageOpen, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import useV2MigrationStore from '../migration/v2_migration'
import session from '../session'
import { settingsOpenedFrom, settingsTab, showSettingsDialog } from '../settings/settings'
import { __ } from '../translation'

const store = useV2MigrationStore()
const showConfirm = ref(false)
const hiding = ref(false)

// The server owns the rule - see `get_v2_migration_nudge`. The store asks, so
// the migration page reads the same answer.
if (session.user.is_admin) {
	store.loadNudge()
}

const show = computed(() => store.nudge.show && store.nudge.waiting > 0 && store.nudge.canMigrate)

function openMigration() {
	settingsTab.value = 'v2-migration'
	settingsOpenedFrom.value = 'sidebar'
	showSettingsDialog.value = true
}

// Hidden on the server, for the whole site: whoever decides v2 is done decides
// it for everyone, and should not be asked again on their next machine. That
// reach is why one click is not enough to do it.
async function hide() {
	hiding.value = true
	try {
		await store.setNudgeHidden(true)
		showConfirm.value = false
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
						store.nudge.waiting === 1
							? __('1 dashboard is still in Insights v2')
							: __(
									'{0} dashboards are still in Insights v2',
									String(store.nudge.waiting),
							  )
					}}
				</div>
			</div>
			<button
				class="mt-0.5 shrink-0 rounded p-0.5 text-ink-gray-5 hover:text-ink-gray-7"
				:title="__('Done with v2. Hide this.')"
				@click="showConfirm = true"
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

	<Dialog v-model="showConfirm" :options="{ title: __('Hide this reminder') }">
		<template #body-content>
			<p class="text-p-base text-ink-gray-7">
				{{
					__(
						'This hides the reminder for everyone on this site, in both v2 and v3. Your v2 dashboards stay as they are, and you can bring the reminder back from Migrate from v2.',
					)
				}}
			</p>
		</template>
		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Cancel')" variant="subtle" @click="showConfirm = false" />
				<Button :label="__('Hide it')" variant="solid" :loading="hiding" @click="hide" />
			</div>
		</template>
	</Dialog>
</template>
