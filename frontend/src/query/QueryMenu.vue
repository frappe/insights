<template>
	<div class="flex flex-shrink-0 space-x-2">
		<Dropdown
			placement="left"
			:button="{ icon: 'more-horizontal', variant: 'outline' }"
			:options="[
				!query.doc.is_stored && !query.doc.is_native_query
					? {
							label: 'Store Query',
							icon: 'bookmark',
							onClick: storeQuery,
					  }
					: null,
				!query.doc.is_saved_as_table
					? {
							label: 'Save as Table',
							icon: 'bookmark',
							onClick: () => (show_save_table_dialog = true),
					  }
					: {
							label: 'Delete Linked Table',
							icon: 'trash-2',
							onClick: () => (show_save_table_dialog = true),
					  },
				{
					label: 'Execute (⌘+E)',
					icon: 'play',
					onClick: query.execute,
				},
				settings.enable_permissions && query.isOwner
					? {
							label: 'Share',
							icon: 'share-2',
							onClick: () => (show_share_dialog = true),
					  }
					: null,
				{
					label: 'Set Alert',
					icon: 'bell',
					onClick: () => (show_alert_dialog = true),
				},
				{
					label: 'Pivot',
					icon: 'git-branch',
					onClick: () => (show_pivot_dialog = true),
				},
				{
					label: 'Unpivot',
					icon: 'git-merge',
					onClick: () => (show_unpivot_dialog = true),
				},
				{
					label: 'Transpose',
					icon: 'rotate-ccw',
					onClick: () => (show_transpose_dialog = true),
				},
				{
					label: 'Reset Transforms',
					icon: 'refresh-ccw',
					onClick: resetPivot,
				},
				{
					label: 'Reset',
					icon: 'refresh-ccw',
					onClick: () => (show_reset_dialog = true),
				},
				!query.doc.is_native_query
					? {
							label: 'View SQL',
							icon: 'help-circle',
							onClick: () => (show_sql_dialog = true),
					  }
					: null,
				{
					label: !query.doc.is_native_query ? 'Write SQL' : 'Build SQL',
					icon: 'codesandbox',
					onClick: () => (show_convert_query_dialog = true),
				},
				{
					label: 'Duplicate',
					icon: 'copy',
					onClick: duplicateQuery,
				},
				{
					label: 'Download CSV',
					icon: 'download',
					onClick: downloadCSV,
				},
				{
					label: 'Delete',
					icon: 'trash-2',
					onClick: () => (show_delete_dialog = true),
				},
			]"
		/>

		<Dialog
			v-model="show_delete_dialog"
			:dismissable="true"
			:options="{
				title: 'Delete Query',
				message: 'Are you sure you want to delete this query?',
				icon: { name: 'trash', appearance: 'danger' },
				actions: [
					{
						label: 'Delete',
						variant: 'solid',
						theme: 'red',
						onClick: () => {
							query.delete.submit().then(() => {
								$router.push('/query')
								show_delete_dialog = false
							})
						},
					},
				],
			}"
		>
		</Dialog>

		<Dialog
			v-model="show_save_table_dialog"
			:dismissable="true"
			:options="{
				title: query.doc.is_saved_as_table ? 'Delete Linked Table' : 'Save as Table',
				message: query.doc.is_saved_as_table
					? 'Are you sure you want to deleted the linked table? You will not be able to use this query as a table in other queries.'
					: 'You can save this query as a table to reuse it in other queries as a table. Tip: Give a proper title to the query before saving it as a table.',
				icon: {
					appearance: 'primary',
					name: query.doc.is_saved_as_table ? 'trash-2' : 'bookmark',
				},
				actions: [
					{
						label: query.doc.is_saved_as_table ? 'Unlink' : 'Save',
						variant: 'solid',
						loading: query.doc.is_saved_as_table
							? query.delete_linked_table?.loading
							: query.save_as_table?.loading,
						onClick: () => {
							const fn = query.doc.is_saved_as_table
								? query.delete_linked_table
								: query.save_as_table
							fn.submit().then(() => {
								show_save_table_dialog = false
							})
						},
					},
				],
			}"
		>
		</Dialog>

		<Dialog
			v-model="show_convert_query_dialog"
			:dismissable="true"
			:options="{
				title: `Convert to ${!query.doc.is_native_query ? 'Native' : 'Builder'} Query`,
				icon: { name: 'info', appearance: 'warning' },
				message: `Are you sure you want to convert this query to a ${
					!query.doc.is_native_query ? 'native' : 'builder'
				} query? This will overwrite the existing query.`,
				actions: [
					{
						label: 'Yes',
						variant: 'solid',
						onClick: () => {
							query.convert.submit().then(() => {
								show_convert_query_dialog = false
							})
						},
					},
				],
			}"
		>
		</Dialog>

		<Dialog
			v-model="show_reset_dialog"
			:dismissable="true"
			:options="{
				title: 'Reset Query',
				message: 'Are you sure you want to reset this query?',
				icon: { name: 'alert-circle', appearance: 'danger' },
				actions: [
					{
						label: 'Reset',
						variant: 'solid',
						theme: 'red',
						onClick: () => {
							query.reset.submit().then(() => {
								show_reset_dialog = false
							})
						},
					},
				],
			}"
		>
		</Dialog>

		<Dialog
			:options="{ title: 'Generated SQL', size: '3xl' }"
			v-model="show_sql_dialog"
			:dismissable="true"
		>
			<template #body-content>
				<div class="relative">
					<p
						class="rounded border bg-gray-100 p-2 text-base text-gray-600"
						style="font-family: 'Fira Code'"
						v-html="formattedSQL"
					></p>
					<Button
						icon="copy"
						variant="outline"
						class="absolute bottom-2 right-2"
						@click="copyToClipboard(query.doc.sql)"
					></Button>
				</div>
			</template>
		</Dialog>

		<Dialog
			:options="{ title: 'Pivot Transform' }"
			v-model="show_pivot_dialog"
			:dismissable="true"
		>
			<template #body-content>
				<div class="space-y-4">
					<Input
						type="select"
						label="Pivot Column"
						v-model="pivot.column"
						:options="pivotOptions"
					/>
					<Input
						type="select"
						label="Index Column"
						v-model="pivot.index"
						:options="indexOptions"
					/>
					<Input
						type="select"
						label="Value Column"
						v-model="pivot.value"
						:options="valueOptions"
					/>
				</div>
			</template>
			<template #actions>
				<Button
					variant="solid"
					@click="() => applyTransform('Pivot', pivot)"
					:disabled="pivotDisabled"
					:loading="query.addTransform?.loading"
				>
					Apply
				</Button>
			</template>
		</Dialog>

		<Dialog
			:options="{ title: 'Unpivot Transform' }"
			v-model="show_unpivot_dialog"
			:dismissable="true"
		>
			<template #body-content>
				<div class="space-y-4">
					<Input
						type="select"
						label="Index Column"
						v-model="unpivot.index_column"
						:options="indexOptions"
					/>
					<Input
						type="text"
						label="Column Label"
						placeholder="eg. Region"
						v-model="unpivot.column_label"
					/>
					<Input
						type="text"
						label="Value Label"
						placeholder="eg. Sales"
						v-model="unpivot.value_label"
					/>
				</div>
			</template>
			<template #actions>
				<Button
					variant="solid"
					@click="() => applyTransform('Unpivot', unpivot)"
					:disabled="unpivotDisabled"
					:loading="query.addTransform?.loading"
				>
					Apply
				</Button>
			</template>
		</Dialog>

		<Dialog
			:options="{ title: 'Transpose' }"
			v-model="show_transpose_dialog"
			:dismissable="true"
		>
			<template #body-content>
				<div class="space-y-4">
					<Input
						type="select"
						label="Index Column"
						v-model="transpose.index_column"
						:options="indexOptions"
					/>
					<Input
						type="text"
						label="Column Label"
						placeholder="eg. Region"
						v-model="transpose.column_label"
					/>
				</div>
			</template>
			<template #actions>
				<Button
					variant="solid"
					@click="() => applyTransform('Transpose', transpose)"
					:disabled="transposeDisabled"
					:loading="query.addTransform?.loading"
				>
					Apply
				</Button>
			</template>
		</Dialog>
	</div>

	<ShareDialog
		v-if="settings.enable_permissions"
		v-model:show="show_share_dialog"
		:resource-type="query.doc.doctype"
		:resource-name="query.doc.name"
	/>

	<AlertDialog
		v-if="query.doc.name"
		v-model:show="show_alert_dialog"
		:queryName="query.doc.name"
	/>
</template>

<script setup>
import AlertDialog from '@/components/AlertDialog.vue'
import ShareDialog from '@/components/ShareDialog.vue'
import { copyToClipboard } from '@/utils'
import settingsStore from '@/stores/settingsStore'
import { useMagicKeys } from '@vueuse/core'
import { Dialog, Dropdown } from 'frappe-ui'
import { computed, inject, nextTick, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const settings = settingsStore().settings

const props = defineProps(['query'])
const query = props.query || inject('query')

const show_save_table_dialog = ref(false)
const show_reset_dialog = ref(false)
const show_delete_dialog = ref(false)
const show_sql_dialog = ref(false)
const show_pivot_dialog = ref(false)
const show_share_dialog = ref(false)
const show_convert_query_dialog = ref(false)
const show_alert_dialog = ref(false)
const show_unpivot_dialog = ref(false)
const show_transpose_dialog = ref(false)

const keys = useMagicKeys()
const cmdE = keys['Meta+E']
watch(cmdE, (value) => value && query.execute())

const pivot = reactive({
	column: null,
	index: null,
	value: null,
})
const unpivot = reactive({
	index_column: null,
	column_label: null,
	value_label: null,
})
const transpose = reactive({
	index_column: null,
	column_label: null,
})

const formattedSQL = computed(() => {
	return query.doc.sql.replaceAll('\n', '<br>').replaceAll('      ', '&ensp;&ensp;&ensp;&ensp;')
})

const router = useRouter()
const $notify = inject('$notify')
function duplicateQuery() {
	query.duplicate.submit().then(async (res) => {
		await nextTick()
		router.push(`/query/build/${res.message}`)
		$notify({
			variant: 'success',
			title: 'Query Duplicated',
		})
	})
}

function storeQuery() {
	query.store.submit().then((res) => {
		$notify({
			variant: 'success',
			title: 'Query Stored',
		})
	})
}

const pivotOptions = computed(() =>
	[''].concat(
		query.columns.indexOptions
			.map((option) => option.label)
			.filter((option) => option !== pivot.index)
	)
)
const indexOptions = computed(() =>
	[''].concat(
		query.columns.indexOptions
			.map((option) => option.label)
			.filter((option) => option !== pivot.column)
	)
)
const valueOptions = computed(() =>
	[''].concat(query.columns.valueOptions.map((option) => option.label))
)

function applyTransform(type, options) {
	query.addTransform
		.submit({
			type,
			options,
		})
		.then(() => {
			show_pivot_dialog.value = false
			show_unpivot_dialog.value = false
			show_transpose_dialog.value = false
			Object.keys(pivot).forEach((key) => (pivot[key] = null))
			Object.keys(unpivot).forEach((key) => (unpivot[key] = null))
			Object.keys(transpose).forEach((key) => (transpose[key] = null))
		})
}

function resetPivot() {
	query.resetTransforms.submit()
}

function downloadCSV() {
	let data = query.results.data
	if (data.length === 0) return
	data[0] = data[0].map((d) => d.label)
	const csvString = data.map((row) => row.join(',')).join('\n')
	const blob = new Blob([csvString], { type: 'text/csv' })
	const url = window.URL.createObjectURL(blob)
	const a = document.createElement('a')
	a.setAttribute('hidden', '')
	a.setAttribute('href', url)
	a.setAttribute('download', `${query.doc.title || 'data'}.csv`)
	document.body.appendChild(a)
	a.click()
	document.body.removeChild(a)
}

const pivotDisabled = computed(() => {
	return !pivot.column || !pivot.index || !pivot.value
})
const unpivotDisabled = computed(() => {
	return !unpivot.index_column || !unpivot.column_label || !unpivot.value_label
})
const transposeDisabled = computed(() => {
	return !transpose.index_column || !transpose.column_label
})
</script>
