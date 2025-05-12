<template>
	<Dialog v-model="show" :options="{ title: title }">
		<template #body-content>
			<p class="text-p-base text-gray-700" v-if="message">
				{{ message }}
			</p>
			<div class="space-y-4">
				<FormControl
					v-for="field in fields"
					v-bind="field"
					v-model="values[field.fieldname]"
					:key="field.fieldname"
				/>
			</div>
			<ErrorMessage class="mt-2" :message="error" />
		</template>
		<template #actions>
			<div class="flex items-center justify-end space-x-2">
				<Button @click="show = false">Cancel</Button>
				<Button
					variant="solid"
					:theme="$props.theme"
					@click="onConfirm"
					:loading="isLoading"
				>
					{{ primaryActionLabel || 'Confirm' }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>
<script>
import { ErrorMessage, FormControl } from 'frappe-ui'

export default {
	name: 'ConfirmDialog',
	props: ['title', 'message', 'theme', 'fields', 'onSuccess', 'primaryActionLabel'],
	data() {
		return {
			show: true,
			error: null,
			isLoading: false,
			values: {},
		}
	},
	components: { FormControl, ErrorMessage },
	methods: {
		onConfirm() {
			this.error = null
			this.isLoading = true
			try {
				let result = this.onSuccess({ hide: this.hide, values: this.values })
				if (result?.then) {
					result
						.then(() => (this.isLoading = false))
						.catch((error) => (this.error = error))
				}
			} catch (error) {
				this.error = error
			} finally {
				this.isLoading = false
				this.hide()
			}
		},
		hide() {
			this.show = false
		},
	},
}
</script>
