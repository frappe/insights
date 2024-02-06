<template>
	<div class="m-2 flex transition duration-200 ease-out">
		<div :class="['w-[22rem] rounded bg-white p-3 shadow-md', variantClasses]">
			<div class="flex items-start">
				<div v-if="icon || variantIcon" class="mr-2 pt-1">
					<FeatherIcon
						:name="icon || variantIcon"
						:class="['h-4 w-4 rounded-full', variantIconClasses, iconClasses]"
					/>
				</div>
				<div>
					<slot>
						<p class="text-base font-medium leading-5 text-gray-900">
							{{ title }}
						</p>
						<p v-if="message" class="text-base text-gray-600">
							<span v-if="containsHTML" v-html="message"></span>
							<span v-else>{{ message }}</span>
						</p>
					</slot>
				</div>
				<div class="ml-auto pl-2">
					<slot name="actions">
						<!-- <button class="grid h-5 w-5 place-items-center rounded hover:bg-gray-100">
							<FeatherIcon name="x" class="h-4 w-4 text-gray-700" />
						</button> -->
					</slot>
				</div>
			</div>
		</div>
	</div>
</template>
<script>
import { FeatherIcon } from 'frappe-ui'
const variant = ['success', 'info', 'warning', 'error']

export default {
	name: 'Toast',
	props: {
		icon: {
			type: String,
		},
		iconClasses: {
			type: String,
		},
		title: {
			type: String,
		},
		message: {
			type: String,
		},
		variant: {
			type: String,
			default: 'info',
		},
	},
	components: {
		FeatherIcon,
	},
	data() {
		return {
			shown: false,
		}
	},
	computed: {
		containsHTML() {
			return this.message?.includes('<')
		},
		variantClasses() {
			if (this.variant === 'success') {
				return 'bg-green-50'
			}
			if (this.variant === 'info') {
				return 'bg-blue-50'
			}
			if (this.variant === 'warning') {
				return 'bg-orange-50'
			}
			if (this.variant === 'error') {
				return 'bg-red-50'
			}
		},
		variantIcon() {
			if (this.variant === 'success') {
				return 'check'
			}
			if (this.variant === 'info') {
				return 'info'
			}
			if (this.variant === 'warning') {
				return 'alert-circle'
			}
			if (this.variant === 'error') {
				return 'x'
			}
		},
		variantIconClasses() {
			if (this.variant === 'success') {
				return 'text-white bg-green-600 p-0.5'
			}
			if (this.variant === 'info') {
				return 'text-white bg-blue-600'
			}
			if (this.variant === 'warning') {
				return 'text-white bg-orange-600'
			}
			if (this.variant === 'error') {
				return 'text-white bg-red-600 p-0.5'
			}
		},
	},
}
</script>
