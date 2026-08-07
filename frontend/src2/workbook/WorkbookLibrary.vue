<script setup lang="ts">
import { Button, Dialog, call } from 'frappe-ui'
import { useTelemetry } from 'frappe-ui/frappe'
import { LayoutDashboard } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createToast } from '../helpers/toasts'
import { __ } from '../translation'

/** A bundle an installed app ships, as it landed on this site. */
export type StandardBundle = {
	workbook: number
	title: string
	app: string
	app_title: string
	dashboards: { name: string; title: string; slug: string; standard_id: string }[]
}

const props = defineProps<{ bundles: StandardBundle[] }>()
const show = defineModel<boolean>({ default: false })

// group by the app the content is for, so an app's dashboards read as one
// attributed section rather than one undifferentiated list
const sections = computed(() => {
	const byApp = new Map<string, StandardBundle[]>()
	for (const bundle of props.bundles) {
		const group = byApp.get(bundle.app_title) ?? []
		group.push(bundle)
		byApp.set(bundle.app_title, group)
	}
	return [...byApp.entries()]
		.map(([app, items]) => ({ app, items }))
		.sort((a, b) => a.app.localeCompare(b.app))
})

const router = useRouter()
const { capture } = useTelemetry()

// the bundle currently being copied, so only its button spins
const duplicating = ref<number | null>(null)

function duplicate(bundle: StandardBundle) {
	duplicating.value = bundle.workbook
	call('insights.api.bundles.duplicate_bundle', { workbook: bundle.workbook })
		.then((result: { workbook: number; dashboard: string | null }) => {
			capture('standard_bundle_duplicated', { app: bundle.app, bundle: bundle.title })
			createToast({ message: __('{0} copied', bundle.title), variant: 'success' })
			router.push(
				result.dashboard
					? `/workbook/${result.workbook}/dashboard/${result.dashboard}`
					: `/workbook/${result.workbook}`,
			)
		})
		.catch(() => {
			createToast({
				message: __('Failed to copy {0}', bundle.title),
				variant: 'error',
			})
		})
		.finally(() => (duplicating.value = null))
}

function open(dashboard: StandardBundle['dashboards'][number]) {
	show.value = false
	router.push(`/dashboards/${dashboard.slug || dashboard.name}`)
}
</script>

<template>
	<Dialog v-model:open="show" :title="__('Library')" size="2xl">
		<template #default>
			<p class="-mt-3 mb-5 text-p-base text-ink-gray-6">
				{{
					__(
						'Dashboards your installed apps ship. They stay as shipped — take a copy to make them yours.',
					)
				}}
			</p>
			<!-- cap the height so the list scrolls inside the dialog rather than
			growing the panel and scrolling the whole overlay -->
			<div class="max-h-[60vh] overflow-y-auto">
				<div v-for="section in sections" :key="section.app" class="mb-6 last:mb-0">
					<div class="mb-2.5 text-p-sm-medium text-ink-gray-5">
						{{ section.app }}
					</div>
					<div class="flex flex-col gap-3">
						<div
							v-for="bundle in section.items"
							:key="bundle.workbook"
							class="rounded border border-outline-gray-1 bg-surface-base p-4"
						>
							<div class="flex items-center justify-between gap-3">
								<div class="truncate text-base-medium text-ink-gray-9">
									{{ bundle.title }}
								</div>
								<Button
									:label="__('Duplicate')"
									:loading="duplicating === bundle.workbook"
									:disabled="!!duplicating"
									@click="duplicate(bundle)"
								/>
							</div>
							<div class="mt-2 flex flex-wrap items-center gap-1">
								<Button
									v-for="dashboard in bundle.dashboards"
									:key="dashboard.name"
									variant="ghost"
									:label="dashboard.title"
									@click="open(dashboard)"
								>
									<template #prefix>
										<LayoutDashboard class="h-4 w-4" stroke-width="1.5" />
									</template>
								</Button>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
