<template>
	<div class="h-fit rounded-md shadow">
		<Dropdown
			placement="right"
			:button="{ icon: 'more-horizontal', appearance: 'white' }"
			:options="[
				{
					label: 'Reset',
					icon: 'refresh-ccw',
					handler: () => (show_reset_dialog = true),
				},
				{
					label: 'View Form',
					icon: 'edit',
					handler: open_form,
				},
				{
					label: 'Delete',
					icon: 'trash-2',
					handler: () => (show_delete_dialog = true),
				},
			]"
		/>

		<Dialog
			:options="{ title: 'Delete Query', icon: { name: 'trash', appearance: 'danger' } }"
			v-model="show_delete_dialog"
			:dismissable="true"
		>
			<template #body-content>
				<p class="text-base text-gray-600">Are you sure you want to delete this query?</p>
			</template>
			<template #actions>
				<Button appearance="danger" :loading="$resources.delete.loading" @click="delete_query"> Yes </Button>
			</template>
		</Dialog>
		<Dialog
			:options="{ title: 'Reset Query', icon: { name: 'alert-circle', appearance: 'danger' } }"
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
							query.reset.submit()
							show_reset_dialog = false
						}
					"
				>
					Yes
				</Button>
			</template>
		</Dialog>
	</div>
</template>

<script>
import { Dialog, Dropdown } from 'frappe-ui'

export default {
	name: 'QueryMenu',
	components: {
		Dialog,
		Dropdown,
	},
	props: ['query'],
	data() {
		return {
			show_reset_dialog: false,
			show_delete_dialog: false,
			hostname: window.location.hostname,
			port: window.location.port ? ':8000' : '',
		}
	},
	resources: {
		delete() {
			return { method: 'frappe.client.delete' }
		},
	},
	methods: {
		open_form() {
			window.open(`http://${this.hostname}${this.port}/app/query/${this.query.doc.name}`, '_blank').focus()
		},
		delete_query() {
			this.$resources.delete.submit(
				{
					doctype: 'Query',
					name: this.query.doc.name,
				},
				{
					onSuccess: () => {
						this.$router.push('/query')
					},
					onError: () => {
						this.$notify({
							title: 'Something went wrong',
							appearance: 'error',
						})
					},
				}
			)
		},
	},
}
</script>
