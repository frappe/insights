<template>
	<div class="h-fit">
		<Dropdown
			placement="left"
			:button="{ icon: 'more-horizontal', appearance: 'minimal' }"
			:options="[
				{
					label: 'Reset',
					icon: 'refresh-ccw',
					handler: () => (show_reset_dialog = true),
				},
				{
					label: 'View SQL',
					icon: 'help-circle',
					handler: () => (show_sql_dialog = true),
				},
				{
					label: 'Duplicate',
					icon: 'copy',
					handler: duplicateQuery,
				},
				{
					label: 'Delete',
					icon: 'trash-2',
					handler: () => (show_delete_dialog = true),
				},
			]"
		/>

		<Dialog
			:options="{
				title: 'Delete Query',
				icon: { name: 'trash', appearance: 'danger' },
			}"
			v-model="show_delete_dialog"
			:dismissable="true"
		>
			<template #body-content>
				<p class="text-base text-gray-600">Are you sure you want to delete this query?</p>
			</template>
			<template #actions>
				<Button
					appearance="danger"
					:loading="query.delete.loading"
					@click="
						() => {
							query.delete.submit().then(() => {
								$router.push('/query')
								show_delete_dialog = false
							})
						}
					"
				>
					Yes
				</Button>
			</template>
		</Dialog>
		<Dialog
			:options="{
				title: 'Reset Query',
				icon: { name: 'alert-circle', appearance: 'danger' },
			}"
			v-model="show_reset_dialog"
			:dismissable="true"
		>
			<template #body-content>
				<p class="text-base text-gray-600">Are you sure you want to reset this query?</p>
			</template>
			<template #actions>
				<Button
					appearance="danger"
					:loading="query.reset.loading"
					@click="
						() => {
							query.reset.submit().then(() => {
								show_reset_dialog = false
							})
						}
					"
				>
					Yes
				</Button>
			</template>
		</Dialog>

		<Dialog :options="{ title: 'Generated SQL' }" v-model="show_sql_dialog" :dismissable="true">
			<template #body-content>
				<p
					class="rounded-md border bg-gray-100 p-2 text-base text-gray-600"
					style="font-family: 'Fira Code'"
					v-html="formattedSQL"
				></p>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { ref, inject, computed, nextTick } from 'vue'
import { Dialog, Dropdown } from 'frappe-ui'
import { useRouter } from 'vue-router'

const query = inject('query')

const show_reset_dialog = ref(false)
const show_delete_dialog = ref(false)
const show_sql_dialog = ref(false)

const formattedSQL = computed(() => {
	return query.doc.sql.replaceAll('\n', '<br>').replaceAll('      ', '&ensp;&ensp;&ensp;&ensp;')
})

const $router = useRouter()
const $notify = inject('$notify')
function duplicateQuery() {
	query.duplicate.submit().then(async (res) => {
		await nextTick()
		$router.push('/query/' + res.message)
		$notify({
			appearance: 'success',
			title: 'Query Duplicated',
		})
	})
}
</script>
