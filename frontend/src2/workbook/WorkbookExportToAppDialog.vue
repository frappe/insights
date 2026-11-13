<script setup lang="ts">
import { CheckCircle2 } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import { getErrorMessage } from '../helpers'
import { __ } from '../translation'
import {
	ExportModule,
	WORKBOOK_NAME_PATTERN,
	exportFilePath,
	getExportModules,
	toWorkbookName,
} from './export_to_app'
import type { Workbook } from './workbook'
import { workbookKey } from './workbook_key'

const show = defineModel<boolean>()
const emit = defineEmits<{ marked: [string] }>()

const workbook = inject(workbookKey) as Workbook

const modules = ref<ExportModule[]>([])

// no default module: a wrong guess writes the workbook into another app's repo
const selected = ref('')
const module = computed(() => modules.value.find((m) => m.module === selected.value))
const moduleOptions = computed(() =>
	modules.value.map((m) => ({ label: m.module, value: m.module, description: m.app })),
)

const name = ref(toWorkbookName(workbook.doc.title))
const nameError = computed(() => {
	if (!name.value) return __('Name the workbook ships under')
	if (!WORKBOOK_NAME_PATTERN.test(name.value)) {
		return __('A name is lowercase letters, digits and "-"')
	}
	return ''
})

const filePath = computed(() => (module.value ? exportFilePath(module.value, name.value) : ''))

const marking = ref(false)
const error = ref('')
const marked = ref('')
const written = computed(() =>
	marked.value ? exportFilePath(module.value as ExportModule, marked.value) : '',
)

getExportModules()
	.then((response) => (modules.value = response))
	.catch((e: any) => (error.value = getErrorMessage(e)))

function submit() {
	if (!selected.value || nameError.value || marking.value) return

	marking.value = true
	error.value = ''
	workbook
		.call('mark_as_standard', { name: name.value, module: selected.value })
		.then((name: string) => (marked.value = name))
		.catch((e: any) => (error.value = getErrorMessage(e)))
		.finally(() => (marking.value = false))
}

function done() {
	show.value = false
	emit('marked', marked.value)
}

// During the export there is nothing to go back to. After it, the workbook has
// a new name. So Done, which reloads, is the only way out.
const locked = computed(() => marking.value || Boolean(marked.value))

const actions = computed(() => {
	if (marked.value) {
		return [{ label: __('Done'), variant: 'solid', onClick: done }]
	}
	return [
		{ label: __('Cancel'), onClick: () => (show.value = false) },
		{
			label: __('Export'),
			variant: 'solid',
			loading: marking.value,
			disabled: !selected.value || Boolean(nameError.value),
			onClick: submit,
		},
	]
})
</script>

<template>
	<Dialog
		v-model:open="show"
		:title="written ? __('Exported to app') : __('Export to app')"
		:actions="actions"
		:dismissible="!locked"
		:show-close-button="!locked"
	>
		<template #default>
			<div v-if="!written" class="flex flex-col gap-4 text-base">
				<div>
					<label class="mb-1.5 block text-xs text-ink-gray-5">{{ __('Module') }}</label>
					<Combobox
						class="w-full"
						:placeholder="__('Select a module')"
						:options="moduleOptions"
						:modelValue="selected"
						@update:modelValue="selected = $event"
					/>
				</div>
				<FormControl
					:label="__('Name')"
					v-model="name"
					placeholder="selling"
					:description="
						__('Every site that takes the file holds the workbook under this name.')
					"
				/>
				<p class="text-p-sm text-ink-gray-6">
					{{
						__(
							'The workbook and its queries, charts and dashboards take readable names, and the app ships them as one file. Outside developer mode the workbook is read-only on every site, including this one.',
						)
					}}
				</p>
				<div v-if="filePath && !nameError" class="flex flex-col gap-1">
					<div class="text-xs text-ink-gray-5">{{ __('Writes') }}</div>
					<div class="break-all font-mono text-xs text-ink-gray-7">{{ filePath }}</div>
				</div>
				<ErrorMessage :message="nameError || error" />
			</div>

			<div v-else class="flex flex-col gap-3 text-base">
				<div class="flex items-start gap-2">
					<CheckCircle2
						class="mt-0.5 h-4 w-4 flex-shrink-0 text-ink-green-6"
						stroke-width="1.5"
					/>
					<p class="text-p-sm text-ink-gray-7">
						{{
							__(
								'{0} is exported to {1} — commit the file below to ship it.',
								workbook.doc.title,
								module?.app || '',
							)
						}}
					</p>
				</div>
				<div class="break-all font-mono text-xs text-ink-gray-7">{{ written }}</div>
			</div>
		</template>
	</Dialog>
</template>
