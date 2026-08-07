<script setup lang="ts">
import { ErrorMessage } from 'frappe-ui'
import { CheckCircle2 } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { getErrorMessage } from '../helpers'
import { __ } from '../translation'
import {
	ExportReport,
	FOLDER_NAME_PATTERN,
	exportDashboard,
	exportTargets,
	itemLabel,
	toFolderName,
} from './export_targets'

const props = defineProps<{ dashboard: string; title: string }>()
const emit = defineEmits<{ exported: [ExportReport] }>()
const show = defineModel<boolean>()

const NEW_WORKBOOK = '__new__'

const apps = computed(() => exportTargets.value?.apps || [])
const appTitle = (name: string) => apps.value.find((a) => a.app === name)?.title || name
// no default app: every installed app is a target, and picking the wrong one
// writes files into someone else's repo
const app = ref('')
const workbooks = computed(() => apps.value.find((a) => a.app === app.value)?.workbooks || [])

const workbook = ref(NEW_WORKBOOK)
const newFolder = ref(toFolderName(props.title))
const newTitle = ref(props.title)

// a shipped workbook belongs to its app, so a switch cannot keep the old choice
watch(app, () => (workbook.value = NEW_WORKBOOK))

const appOptions = computed(() => [
	{ label: __('Select an app'), value: '' },
	...apps.value.map((a) => ({ label: a.title, value: a.app })),
])
const workbookOptions = computed(() => [
	...workbooks.value.map((w) => ({ label: `${w.title} (${w.folder})`, value: w.folder })),
	{ label: __('New workbook…'), value: NEW_WORKBOOK },
])

const isNewWorkbook = computed(() => workbook.value === NEW_WORKBOOK)
const nameError = computed(() => {
	if (!isNewWorkbook.value) return ''
	if (!newFolder.value) return __('Enter a folder name for the new workbook')
	if (!FOLDER_NAME_PATTERN.test(newFolder.value)) {
		return __('A workbook folder must be lowercase letters, digits, "-" or "_"')
	}
	return ''
})

const exporting = ref(false)
const error = ref('')
const report = ref<ExportReport>()

function submit() {
	if (!app.value || nameError.value || exporting.value) return

	exporting.value = true
	error.value = ''
	exportDashboard({
		dashboard: props.dashboard,
		app: app.value,
		folder: isNewWorkbook.value ? newFolder.value : workbook.value,
		workbook_title: isNewWorkbook.value ? newTitle.value : undefined,
	})
		.then((response) => (report.value = response))
		.catch((e: any) => (error.value = getErrorMessage(e)))
		.finally(() => (exporting.value = false))
}

function done() {
	emit('exported', report.value as ExportReport)
	show.value = false
}

// mid-export there is nothing to go back to, and once the report exists the
// dashboard has already left this workbook — so Done is the only way out, and
// it is the one path that takes the builder with it
const locked = computed(() => exporting.value || Boolean(report.value))

const actions = computed(() => {
	if (report.value) {
		return [{ label: __('Done'), variant: 'solid', onClick: done }]
	}
	return [
		{ label: __('Cancel'), onClick: () => (show.value = false) },
		{
			label: __('Export'),
			variant: 'solid',
			loading: exporting.value,
			disabled: !app.value || Boolean(nameError.value),
			onClick: submit,
		},
	]
})
</script>

<template>
	<Dialog
		v-model:open="show"
		:title="report ? __('Exported to {0}', appTitle(report.app)) : __('Export to App')"
		:actions="actions"
		:dismissible="!locked"
		:show-close-button="!locked"
	>
		<template #default>
			<div v-if="!report" class="flex flex-col gap-4 text-base">
				<p class="text-p-sm text-ink-gray-6">
					{{
						__(
							'Writes this dashboard, its charts and their queries into the app as standard content. The dashboard leaves this workbook for the one the app ships.',
						)
					}}
				</p>
				<FormControl type="select" :label="__('App')" v-model="app" :options="appOptions" />
				<FormControl
					type="select"
					:label="__('Workbook')"
					v-model="workbook"
					:options="workbookOptions"
				/>
				<template v-if="isNewWorkbook">
					<FormControl
						:label="__('Workbook Folder')"
						v-model="newFolder"
						placeholder="sales_reports"
					/>
					<FormControl
						:label="__('Workbook Title')"
						v-model="newTitle"
						placeholder="Sales Reports"
					/>
					<ErrorMessage :message="nameError" />
				</template>
				<ErrorMessage :message="error" />
			</div>

			<div v-else class="flex flex-col gap-4 text-base">
				<div class="flex items-start gap-2">
					<CheckCircle2
						class="mt-0.5 h-4 w-4 flex-shrink-0 text-ink-green-6"
						stroke-width="1.5"
					/>
					<p class="text-p-sm text-ink-gray-7">
						{{
							__(
								'{0} is now standard content of {1}. It has left this workbook for the one {1} ships — commit the files below to ship it.',
								props.title,
								appTitle(report.app),
							)
						}}
					</p>
				</div>
				<div class="flex flex-col gap-1">
					<div class="text-sm-medium text-ink-gray-7">
						{{ __('{0}/{1}', report.app, report.folder) }}
					</div>
					<div
						class="flex max-h-64 flex-col divide-y divide-outline-gray-1 overflow-y-auto rounded border border-outline-gray-2"
					>
						<div
							v-for="item in report.items"
							:key="item.standard_id"
							class="flex flex-col px-3 py-2"
						>
							<div class="text-sm text-ink-gray-8">
								{{ itemLabel(item) }}
							</div>
							<div class="font-mono text-xs text-ink-gray-5">{{ item.path }}</div>
						</div>
					</div>
					<div class="text-xs text-ink-gray-5">
						{{
							report.written.length
								? __('{0} files written', String(report.written.length))
								: __('No file changed — the app already ships exactly this')
						}}
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
