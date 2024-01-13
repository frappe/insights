<template>
	<div class="flex flex-shrink-0 space-x-2">
		<Dropdown
			placement="right"
			:button="{ icon: 'more-horizontal', variant: 'outline' }"
			:options="[
				!query.doc.is_stored
					? {
							label: 'Store Query',
							icon: 'bookmark',
							onClick: storeQuery,
					  }
					: {
							label: 'Unstore Query',
							icon: BookmarkMinus,
							onClick: unstoreQuery,
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
					onClick: query.downloadResults,
				},
				{
					label: query.doc.is_assisted_query
						? 'Switch to Classic Query Builder'
						: 'Switch to Visual Query Builder',
					icon: 'toggle-left',
					onClick: () => (show_switch_dialog = true),
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
			v-model="show_switch_dialog"
			:dismissable="true"
			:options="{
				title: query.doc.is_assisted_query
					? 'Switch to Classic Query Builder'
					: 'Switch to Visual Query Builder',
				message: query.doc.is_assisted_query
					? 'All the changes you have made in the query will be preserved. However, if you make any changes in the Classic Query Builder, they will be lost when you switch back to the Visual Query Builder. Are you sure you want to continue?'
					: 'All the changes you have made in the Classic Query Builder will be converted to the Visual Query Builder. Are you sure you want to continue?',
				icon: { name: 'toggle-left', appearance: 'warning' },
				actions: [
					{
						label: 'Switch',
						variant: 'solid',
						onClick: () =>
							query.switchQueryBuilder().then(() => (show_switch_dialog = false)),
					},
				],
			}"
		/>

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
import { BookmarkMinus } from 'lucide-vue-next'
import { computed, inject, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
const settings = settingsStore().settings

const props = defineProps(['query'])
const query = props.query || inject('query')

const show_delete_dialog = ref(false)
const show_sql_dialog = ref(false)
const show_share_dialog = ref(false)
const show_alert_dialog = ref(false)
const show_switch_dialog = ref(false)

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

function unstoreQuery() {
	query.unstore().then((res) => {
		$notify({
			variant: 'success',
			title: 'Query Unstored',
		})
	})
}
</script>
