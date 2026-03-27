<script setup lang="ts">
import { Combobox, MultiSelect } from 'frappe-ui'
import { Sparkles } from 'lucide-vue-next'
import { computed, inject, ref, watch } from 'vue'
import { generateQuery } from '../../api/ai'
import { getDataSourceList } from '../../data_source/data_source'
import useTableStore from '../../data_source/tables'
import { toOptions } from '../../helpers'
import { __ } from '../../translation'
import type { Operation } from '../../types/query.types'
import { Query } from '../query'

const showDialog = defineModel<boolean>()
const query = inject('query') as Query

// ── State ─────────────────────────────────────────────────────────────────────

const question = ref('')
const selectedDataSource = ref('')
const selectedTables = ref<string[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

// ── Derive tables used in current operations ──────────────────────────────────

function getTablesFromOperations(operations: Operation[], forDataSource: string): string[] {
	const tables: string[] = []
	for (const op of operations) {
		if (
			op.type === 'source' &&
			op.table.type === 'table' &&
			op.table.data_source === forDataSource
		) {
			tables.push(op.table.table_name)
		}
		if (op.type === 'join' && op.table.type === 'table' && op.table.data_source === forDataSource) {
			tables.push(op.table.table_name)
		}
	}
	return [...new Set(tables)]
}

// ── Derived ───────────────────────────────────────────────────────────────────

const isModify = computed(() => (query?.doc.operations?.length ?? 0) > 0)

const dialogTitle = computed(() =>
	isModify.value ? __('Modify Query with AI') : __('Generate Query with AI'),
)

const primaryLabel = computed(() => (isModify.value ? __('Modify') : __('Generate')))

const isValid = computed(
	() =>
		question.value.trim().length > 0 &&
		selectedDataSource.value.length > 0 &&
		selectedTables.value.length > 0,
)

// ── Data Sources ──────────────────────────────────────────────────────────────

const sources = getDataSourceList()
const dataSourceOptions = computed(() =>
	toOptions(sources.value, { label: 'title', value: 'name', description: 'database_type' }),
)

// ── Tables ────────────────────────────────────────────────────────────────────

const tableStore = useTableStore()

const tableOptions = computed(() => {
	const rows = tableStore.tables[selectedDataSource.value] || []
	return rows.map((t) => ({ label: t.table_name, value: t.table_name }))
})

// Fetch tables when data source changes; also clear selection (unless prefilling)
let prefilling = false
watch(
	selectedDataSource,
	(ds) => {
		if (!prefilling) selectedTables.value = []
		if (ds) tableStore.getTables(ds)
	},
	{ flush: 'sync' },
)

// ── Prefill on open ───────────────────────────────────────────────────────────

watch(
	showDialog,
	(open) => {
		if (!open) return

		error.value = null

		const ds = query?.dataSource
		if (!ds) return

		prefilling = true
		selectedDataSource.value = ds
		selectedTables.value = getTablesFromOperations(query.doc.operations as Operation[], ds)
		prefilling = false
	},
	{ immediate: true },
)

// ── Submit ────────────────────────────────────────────────────────────────────

async function submit() {
	if (!isValid.value || loading.value) return

	error.value = null
	loading.value = true

	try {
		const params: Parameters<typeof generateQuery>[0] = {
			question: question.value.trim(),
			data_source: selectedDataSource.value,
			table_names: selectedTables.value,
		}

		if (isModify.value) {
			params.current_operations = query.doc.operations as Operation[]
		}

		const result = await generateQuery(params)

		if (result.error || !result.operations) {
			error.value = result.error ?? __('Generation failed. Please try again.')
			return
		}

		query.setOperations(result.operations)
		showDialog.value = false
	} catch (e: any) {
		error.value = e?.message ?? __('An unexpected error occurred.')
	} finally {
		loading.value = false
	}
}

function close() {
	if (loading.value) return
	showDialog.value = false
}
</script>

<template>
	<Dialog :modelValue="showDialog" @update:modelValue="close">
		<template #body>
			<div class="rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
				<!-- Header -->
				<div class="mb-4 flex items-center justify-between">
					<div class="flex items-center gap-2">
						<Sparkles class="h-4 w-4 text-gray-600" stroke-width="1.5" />
						<h3 class="text-xl font-semibold leading-6 text-gray-900">
							{{ dialogTitle }}
						</h3>
					</div>
					<Button variant="ghost" icon="x" size="sm" @click="close" :disabled="loading" />
				</div>

				<!-- Fields -->
				<div class="flex flex-col gap-4">
					<!-- Question -->
					<div>
						<label class="mb-1 block text-xs text-gray-600">
							{{ __('What do you want to know?') }}
						</label>
						<FormControl
							type="textarea"
							v-model="question"
							:placeholder="__('e.g. Show total sales by region for the last 30 days')"
							:disabled="loading"
							:rows="3"
							@keydown.meta.enter="submit"
							@keydown.ctrl.enter="submit"
						/>
					</div>

					<!-- Data Source -->
					<div>
						<label class="mb-1 block text-xs text-gray-600">
							{{ __('Data Source') }}
						</label>
						<Combobox
							:placeholder="__('Select a data source')"
							:options="dataSourceOptions"
							:disabled="loading"
							:open-on-focus="true"
							v-model="selectedDataSource"
						/>
					</div>

					<!-- Tables -->
					<div>
						<label class="mb-1 block text-xs text-gray-600">
							{{ __('Tables') }}
						</label>
						<MultiSelect
							:placeholder="
								selectedDataSource ? __('Select tables') : __('Select a data source first')
							"
							:options="tableOptions"
							:loading="tableStore.loading"
							:disabled="loading || !selectedDataSource"
							v-model="selectedTables"
						/>
					</div>

					<!-- Error -->
					<div
						v-if="error"
						class="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
					>
						{{ error }}
					</div>
				</div>

				<!-- Actions -->
				<div class="mt-5 flex items-center justify-end gap-2">
					<Button variant="outline" :label="__('Cancel')" :disabled="loading" @click="close" />
					<Button
						variant="solid"
						:label="primaryLabel"
						:loading="loading"
						:disabled="!isValid"
						@click="submit"
					>
						<template #prefix>
							<Sparkles class="h-3 w-3" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
