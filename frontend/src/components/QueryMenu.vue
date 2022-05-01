<template>
	<div>
		<Popover :show="menu_open" placement="bottom-end">
			<template #target>
				<button
					class="menu-btn cursor-pointer rounded-md bg-gray-100 p-1.5 text-gray-700"
					@click="menu_open = !menu_open"
				>
					<FeatherIcon name="more-vertical" class="h-4 w-4" />
				</button>
			</template>
			<template #content>
				<div
					class="mt-1 min-w-[12rem] rounded bg-white p-1 text-base text-gray-600 shadow-md ring-1 ring-black ring-opacity-5"
				>
					<a
						class="flex cursor-pointer items-center p-2 hover:bg-gray-50"
						:href="`http://${hostname}${port}/app/query/${query.name}`"
						target="_blank"
					>
						<FeatherIcon name="edit" class="mr-2 h-4 w-4" />View Form
					</a>
					<div
						class="flex cursor-pointer items-center p-2 text-red-600 hover:bg-gray-50"
						@click="show_delete_dialog = true"
					>
						<FeatherIcon name="trash" class="mr-2 h-4 w-4" />Delete
					</div>
				</div>
			</template>
		</Popover>

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
	</div>
</template>

<script>
import { Dialog } from 'frappe-ui'

export default {
	name: 'Query Menu',
	components: {
		Dialog,
	},
	props: ['query'],
	data() {
		return {
			menu_open: false,
			show_delete_dialog: false,
			hostname: window.location.hostname,
			port: window.location.port ? ':8000' : '',
		}
	},
	mounted() {
		this.outside_click_listener = (e) => {
			if (e.target.closest('.menu-btn') || e.target.classList.contains('menu-btn')) {
				return
			}
			this.menu_open = false
		}
		document.addEventListener('click', this.outside_click_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
	resources: {
		delete() {
			return { method: 'frappe.client.delete' }
		},
	},
	methods: {
		delete_query() {
			// this.$resources.delete.submit(
			// 	{
			// 		doctype: 'Query',
			// 		name: this.query.name,
			// 	},
			// 	{
			// 		onSuccess: () => {
			// 			this.$router.push('/query')
			// 		},
			// 		onError: () => {
			// 			this.$notify({
			// 				title: 'Something went wrong',
			// 				color: 'red',
			// 				icon: 'alert-circle',
			// 			})
			// 		},
			// 	}
			// )
		},
	},
}
</script>
