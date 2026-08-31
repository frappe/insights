<script setup>
import { MIGRATION_URL, openInsightsV3, useV2MigrationNudge } from '@/utils/v2migration'
import { AlertTriangle } from 'lucide-vue-next'
import { ref } from 'vue'

const showDetailsDialog = ref(false)
const { waiting, canMigrate } = useV2MigrationNudge()
</script>

<template>
	<div class="rounded-lg border border-amber-200 bg-amber-50/60 p-3.5 shadow-sm">
		<div class="flex items-start gap-2.5">
			<AlertTriangle class="mt-0.5 h-4.5 w-4.5 flex-shrink-0 text-amber-700" />
			<div class="min-w-0 flex-1">
				<h2 class="text-p-base font-semibold text-gray-900">
					Insights v2 is being discontinued
				</h2>
				<p class="mt-1 text-p-sm text-gray-700">
					You are using Insights v2. A future release will remove it.
					<template v-if="waiting">
						Insights v3 can convert your dashboards for you.
					</template>
					<template v-else>Switch to v3 to avoid disruption.</template>
				</p>
			</div>
			<div class="ml-2 flex-shrink-0 self-center">
				<Button variant="outline" @click="showDetailsDialog = true">Learn more</Button>
			</div>
		</div>
	</div>

	<Dialog
		v-model="showDetailsDialog"
		:options="{
			title: 'Insights v2 is being discontinued',
			size: 'lg',
		}"
	>
		<template #body-content>
			<div class="space-y-4 text-base leading-relaxed text-gray-700">
				<div>
					<h3 class="mb-1.5 text-base font-semibold text-gray-900">What's happening?</h3>
					<p>
						You are using Insights v2. A future release will remove it. After that
						update, v2 is no longer reachable.
					</p>
					<p class="mt-2">
						v2 gets no new features and no security fixes. Insights v3 has replaced it.
					</p>
				</div>

				<div>
					<h3 class="mb-1.5 text-base font-semibold text-gray-900">
						What do you need to do?
					</h3>

					<template v-if="waiting && canMigrate">
						<p>
							Insights v3 can convert your dashboards for you. It rebuilds each one in
							v3, then runs both versions and compares the numbers.
						</p>
						<p class="mt-2">
							Open the migration to see what happens to each dashboard before anything
							moves. You pick which dashboards to move.
							<strong>{{ waiting }}</strong>
							{{ waiting === 1 ? 'is waiting' : 'are waiting' }}.
						</p>
					</template>

					<template v-else-if="waiting">
						<p>
							Insights v3 can convert your dashboards for you. It rebuilds each one in
							v3, then runs both versions and compares the numbers.
						</p>
						<p class="mt-2">
							Ask an Insights administrator to run the migration. Only an
							administrator can start it.
						</p>
					</template>

					<template v-else>
						<p>
							Open Insights v3 and build your dashboards there. Start with the ones
							your team uses every day.
						</p>
					</template>

					<p class="mt-2">The migration only reads v2. Nothing you have there changes.</p>
				</div>

				<div>
					<h3 class="mb-1.5 text-base font-semibold text-gray-900">Need help?</h3>
					<p>
						Join the
						<a
							href="https://t.me/frappeinsights"
							target="_blank"
							class="text-blue-600 underline hover:text-blue-700"
							>Telegram community</a
						>
						for migration support, or
						<a
							href="https://frappecloud.com/support"
							target="_blank"
							class="text-blue-600 underline hover:text-blue-700"
							>create a support ticket</a
						>
						if you're on Frappe Cloud.
					</p>
				</div>
			</div>

			<div class="mt-5 flex justify-end gap-2">
				<Button v-if="waiting && canMigrate" variant="subtle" @click="openInsightsV3()">
					Open Insights v3
				</Button>
				<Button
					variant="solid"
					@click="openInsightsV3(waiting && canMigrate ? MIGRATION_URL : '/insights')"
				>
					{{ waiting && canMigrate ? 'Review migration' : 'Open Insights v3' }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>
