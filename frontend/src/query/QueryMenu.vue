<template>
	<div class="flex flex-shrink-0 space-x-2">
		<Dropdown
			placement="left"
			:button="{ icon: 'more-horizontal', variant: 'outline' }"
			:options="[
				!query.doc.is_stored
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
				!query.doc.is_native_query
					? {
							label: 'View SQL',
							icon: 'help-circle',
							onClick: () => (show_sql_dialog = true),
					  }
					: null,
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
							useQueryStore()
								.delete(query.doc.name)
								.then(() => {
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
						loading: query.loading,
						onClick: () => {
							const fn = query.doc.is_saved_as_table
								? query.delete_linked_table
								: query.save_as_table
							fn().then(() => {
								show_save_table_dialog = false
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
import useQueryStore from '@/stores/queryStore'
import settingsStore from '@/stores/settingsStore'
import { copyToClipboard } from '@/utils'
import { useMagicKeys } from '@vueuse/core'
import { Dialog, Dropdown } from 'frappe-ui'
import { computed, inject, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

const settings = settingsStore().settings

const props = defineProps(['query'])
const query = props.query || inject('query')

const show_save_table_dialog = ref(false)
const show_delete_dialog = ref(false)
const show_sql_dialog = ref(false)
const show_share_dialog = ref(false)
const show_alert_dialog = ref(false)

const keys = useMagicKeys()
const cmdE = keys['Meta+E']
watch(cmdE, (value) => value && query.execute())

const formattedSQL = computed(() => {
	return query.doc.sql.replaceAll('\n', '<br>').replaceAll('      ', '&ensp;&ensp;&ensp;&ensp;')
})

const router = useRouter()
const $notify = inject('$notify')
function duplicateQuery() {
	query.duplicate().then(async (query_name) => {
		await nextTick()
		router.push(`/query/build/${query_name}`)
		$notify({
			variant: 'success',
			title: 'Query Duplicated',
		})
	})
}

function storeQuery() {
	query.store().then((res) => {
		$notify({
			variant: 'success',
			title: 'Query Stored',
		})
	})
}

function downloadCSV() {
	let data = query.doc.results
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
</script>
