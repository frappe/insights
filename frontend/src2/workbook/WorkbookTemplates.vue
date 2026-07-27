<script setup lang="ts">
import { Badge, Button, Dialog, call } from 'frappe-ui'
import { CheckCircle2, LayoutTemplate } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { createToast } from '../helpers/toasts'
import { useTelemetry } from 'frappe-ui/frappe'
import { __ } from '../translation'

export type WorkbookTemplate = {
	name: string
	title: string
	description: string
	notes: string | null
	module: string
	app: string
	app_title: string
	version: number
	has_data: boolean
	preview_image: string | null
	imported_workbook: number | null
	imported_version: number | null
	update_available: boolean
	customized: boolean
}

const props = defineProps<{ templates: WorkbookTemplate[] }>()
const emit = defineEmits<{ refresh: [] }>()
const show = defineModel<boolean>({ default: false })

// group by the app each template is for, so an app's dashboards read as one
// attributed section rather than one undifferentiated grid
const sections = computed(() => {
	const byApp = new Map<string, WorkbookTemplate[]>()
	for (const template of props.templates) {
		const group = byApp.get(template.app_title) ?? []
		group.push(template)
		byApp.set(template.app_title, group)
	}
	return [...byApp.entries()]
		.map(([app, items]) => ({ app, items }))
		.sort((a, b) => a.app.localeCompare(b.app))
})

const router = useRouter()
const { capture } = useTelemetry()

// name of the template currently being imported, so only its card spins
const importing = ref<string | null>(null)

function importTemplate(template: WorkbookTemplate) {
	importing.value = template.name
	call('insights.api.templates.create_workbook_from_template', {
		template_name: template.name,
	})
		.then((result: { workbook: number; dashboard: string | null }) => {
			capture('workbook_template_imported', {
				template: template.name,
				app: template.app,
				module: template.module,
			})
			createToast({ message: __('{0} imported', template.title), variant: 'success' })
			router.push(
				result.dashboard
					? `/workbook/${result.workbook}/dashboard/${result.dashboard}`
					: `/workbook/${result.workbook}`,
			)
		})
		.catch(() => {
			createToast({
				message: __('Failed to import {0}', template.title),
				variant: 'error',
			})
		})
		.finally(() => (importing.value = null))
}

function openImported(template: WorkbookTemplate) {
	// usage is tracked centrally via `workbook_template_used` on workbook load,
	// which covers every open path (list, direct URL, here) — no event needed here
	router.push(`/workbook/${template.imported_workbook}`)
}

// name of the template currently updating, so only its card's button spins
const updating = ref<string | null>(null)
// a customized copy is confirmed before its edits are overwritten
const confirmTarget = ref<WorkbookTemplate | null>(null)
const showConfirm = ref(false)

function updateTemplate(template: WorkbookTemplate) {
	if (template.customized) {
		confirmTarget.value = template
		showConfirm.value = true
		return
	}
	runUpdate(template)
}

function runUpdate(template: WorkbookTemplate) {
	showConfirm.value = false
	updating.value = template.name
	call('insights.api.templates.update_workbook_from_template', {
		template_name: template.name,
	})
		.then(() => {
			createToast({ message: __('{0} updated', template.title), variant: 'success' })
			emit('refresh')
		})
		.catch(() => {
			createToast({
				message: __('Failed to update {0}', template.title),
				variant: 'error',
			})
		})
		.finally(() => (updating.value = null))
}
</script>

<template>
	<Dialog v-model:open="show" :title="__('Workbook Library')" size="4xl">
		<template #default>
			<p class="mb-5 text-p-base text-ink-gray-6 -mt-3">
				{{
					__(
						'Ready-made dashboards bundled with your installed apps. Import one to add it to your workbooks — it becomes available to everyone on your site.',
					)
				}}
			</p>
			<!-- cap the height so the cards scroll inside the dialog rather than
			growing the panel and scrolling the whole overlay -->
			<div class="max-h-[60vh] overflow-y-auto">
				<!-- one section per app, headed by the app's title — a single app
				just reads as one section -->
				<div v-for="section in sections" :key="section.app" class="mb-6 last:mb-0">
					<div class="mb-2.5 text-p-sm-medium text-ink-gray-5">
						{{ section.app }}
					</div>
					<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
						<div
							v-for="template in section.items"
							:key="template.name"
							class="col-span-1 flex flex-col overflow-hidden rounded border border-outline-gray-1 bg-surface-base"
						>
							<div
								class="h-52 w-full border-b border-outline-gray-1 bg-surface-gray-1"
							>
								<img
									v-if="template.preview_image"
									:src="template.preview_image"
									:alt="template.title"
									class="h-full w-full object-cover object-top"
								/>
								<div v-else class="flex h-full w-full items-center justify-center">
									<LayoutTemplate
										class="h-8 w-8 text-ink-gray-4"
										stroke-width="1.5"
									/>
								</div>
							</div>
							<div class="flex flex-1 flex-col p-4">
								<div class="flex items-center justify-between gap-2">
									<div class="truncate text-base-medium text-ink-gray-9">
										{{ template.title }}
									</div>
									<Badge v-if="template.module" theme="gray">
										{{ template.module }}
									</Badge>
								</div>
								<div class="mt-1.5 line-clamp-2 text-p-sm text-ink-gray-6">
									{{ template.description }}
								</div>

								<div
									v-if="!template.has_data && !template.imported_workbook"
									class="mt-2 text-p-sm text-ink-amber-6"
								>
									{{
										__(
											'No data found on this site — dashboards may look empty.',
										)
									}}
								</div>

								<div
									v-if="template.update_available"
									class="mt-2 text-p-sm text-ink-blue-3"
								>
									{{ __('A newer version is available.') }}
								</div>

								<div class="mt-4 flex items-center gap-2">
									<template v-if="template.imported_workbook">
										<div
											class="flex items-center gap-1 text-p-sm text-ink-green-6"
										>
											<CheckCircle2 class="h-4 w-4" />
											{{ __('Imported') }}
										</div>
										<div class="ml-auto flex items-center gap-2">
											<Button
												v-if="template.update_available"
												:loading="updating === template.name"
												:disabled="!!updating"
												@click="updateTemplate(template)"
											>
												{{ __('Update') }}
											</Button>
											<Button @click="openImported(template)">
												{{ __('Open') }}
											</Button>
										</div>
									</template>
									<Button
										v-else
										class="ml-auto"
										:loading="importing === template.name"
										:disabled="!!importing"
										@click="importTemplate(template)"
									>
										{{ __('Import') }}
									</Button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>

	<Dialog
		v-model:open="showConfirm"
		:title="__('Replace your changes?')"
		:message="
			__(
				'This dashboard has been edited on your site. Updating replaces its contents with the latest version — your changes will be lost.',
			)
		"
		:actions="[
			{
				label: __('Update'),
				variant: 'solid',
				theme: 'red',
				onClick: () => confirmTarget && runUpdate(confirmTarget),
			},
		]"
	/>
</template>
