<script setup>
import sessionStore from '@/stores/sessionStore'
import { AlertTriangle } from 'lucide-vue-next'
import { ref } from 'vue'

const session = sessionStore()
const showDetailsDialog = ref(false)

function switchToV3() {
	session
		.updateDefaultVersion(
			session.user.default_version === 'v2' ? '' : session.user.default_version,
		)
		.then(() => {
			window.location.href = '/insights'
		})
}
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
					You are currently using Insights v2. This version will be removed in an upcoming
					update. Switch to v3 now to avoid disruption.
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
						You are currently using Insights v2. This version will be removed in an
						upcoming release. Once you update, v2 will no longer be accessible. Insights
						v3 is already available with a better experience and ongoing improvements.
					</p>
					<p class="mt-2">
						New features and security fixes for v2 have stopped. We recommend migrating
						before your next update.
					</p>
				</div>

				<div>
					<h3 class="mb-1.5 text-base font-semibold text-gray-900">
						What do you need to do?
					</h3>
					<p>
						Open Insights v3 in a new tab and recreate your important dashboards and
						queries there. Start with the ones your team uses every day.
					</p>
					<p class="mt-2">
						Automatic migration from v2 to v3 isn't possible because the two versions
						are built differently. An automated transfer would likely break your
						dashboards and queries anyway. Your existing work in v2 stays untouched
						until the removal date, so you can refer to it while you migrate.
					</p>
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
				<Button variant="subtle" @click="showDetailsDialog = false">Close</Button>
				<Button variant="solid" @click="switchToV3">Open Insights v3</Button>
			</div>
		</template>
	</Dialog>
</template>
