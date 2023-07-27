<template>
	<teleport to="#frappeui-toast-root">
		<transition :name="position.includes('top') ? 'toast-top' : 'toast-bottom'">
			<div v-if="shown" :class="['pointer-events-auto m-2 transition duration-200 ease-out']">
				<div :class="['w-[24rem] max-w-xl rounded bg-white p-3 shadow', variantClasses]">
					<div class="flex items-start">
						<div v-if="icon || variantIcon" class="mr-2">
							<FeatherIcon
								:name="icon || variantIcon"
								:class="['h-5 w-5 rounded-full', variantIconClasses, iconClasses]"
							/>
						</div>
						<div>
							<slot>
								<p class="text-base font-medium text-gray-900">
									{{ title }}
								</p>
								<p v-if="message" class="mt-1 text-base text-gray-600">
									<span v-if="containsHTML" v-html="message"></span>
									<span v-else>{{ message }}</span>
								</p>
							</slot>
						</div>
						<div class="ml-auto pl-2">
							<slot name="actions">
								<button
									class="grid h-5 w-5 place-items-center rounded hover:bg-gray-100"
									@click="shown = false"
								>
									<FeatherIcon name="x" class="h-4 w-4 text-gray-700" />
								</button>
							</slot>
						</div>
					</div>
				</div>
			</div>
		</transition>
	</teleport>
</template>
<script>
import { FeatherIcon } from 'frappe-ui'
const positions = ['top-right', 'top-left', 'bottom-right', 'bottom-left']
const variant = ['success', 'info', 'warning', 'error']

export default {
	name: 'Toast',
	props: {
		position: {
			type: String,
			default: 'bottom-right',
		},
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
		timeout: {
			type: Number,
			default: 5,
		},
	},
	components: {
		FeatherIcon,
	},
	created() {
		if (!document.getElementById('frappeui-toast-root')) {
			const root = document.createElement('div')
			root.id = 'frappeui-toast-root'
			Object.assign(root.style, {
				position: 'fixed',
				display: 'flex',
				top: '16px',
				right: '16px',
				bottom: '16px',
				left: '16px',
				zIndex: '9999',
				pointerEvents: 'none',
				padding: '1rem',
				'flex-direction': 'column',
				'justify-content': 'end',
				'align-items': 'end',
			})
			document.body.appendChild(root)
		}
	},
	mounted() {
		this.shown = true
		setTimeout(() => {
			this.shown = false
		}, this.timeout * 1000)
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
		transitionProps() {
			let props = {
				enterActiveClass: 'transition duration-200 ease-out',
				enterFromClass: 'opacity-0',
				enterToClass: 'translate-y-0 opacity-100',
				leaveActiveClass: 'transition duration-100 ease-in',
				leaveFromClass: 'scale-100 translate-y-0 opacity-100',
				leaveToClass: 'scale-75 translate-y-4 opacity-0',
			}
			if (this.position.includes('top')) {
				props.enterFromClass += ' -translate-y-12'
			}
			if (this.position.includes('bottom')) {
				props.enterFromClass += ' translate-y-12'
			}
			return props
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
<style>
.toast-top-enter-active,
.toast-bottom-enter-active {
	transition: all 200ms ease-out;
}
.toast-top-leave-active,
.toast-bottom-leave-active {
	transition: all 100ms ease-in;
}
.toast-top-enter-from,
.toast-bottom-enter-from {
	opacity: 0;
	transform: translateY(0);
}
.toast-top-enter-to,
.toast-bottom-enter-to {
	opacity: 1;
	transform: translateY(0);
}
</style>
