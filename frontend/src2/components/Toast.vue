<template>
	<div class="m-2 flex transition duration-200 ease-out">
		<div :class="['w-[22rem] rounded bg-surface-base p-3 shadow-md', variantClasses]">
			<div class="flex items-start">
				<div v-if="iconComponent" class="mr-2 pt-1">
					<component
						:is="iconComponent"
						:class="['h-4 w-4 rounded-full', variantIconClasses, iconClasses]"
					/>
				</div>
				<div>
					<slot>
						<p class="text-p-base-medium text-ink-gray-8">
							{{ title }}
						</p>
						<p v-if="message" class="text-p-sm text-ink-gray-5">
							{{ message }}
						</p>
					</slot>
				</div>
				<div class="ml-auto pl-2">
					<slot name="actions" />
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Check, CircleAlert, Info, X } from 'lucide-vue-next'
import { computed, type Component } from 'vue'
import { ToastVariant } from '../helpers/toasts'

const props = defineProps<{
	title: string
	message?: string
	variant: ToastVariant
	icon?: Component
	iconClasses?: string
}>()

const variantClasses = computed(() => {
	if (props.variant === 'success') {
		return 'bg-surface-green-1'
	}
	if (props.variant === 'info') {
		return 'bg-surface-blue-1'
	}
	if (props.variant === 'warning') {
		return 'bg-surface-orange-1'
	}
	if (props.variant === 'error') {
		return 'bg-surface-red-1'
	}
})

const variantIcon = computed(() => {
	if (props.variant === 'success') {
		return Check
	}
	if (props.variant === 'info') {
		return Info
	}
	if (props.variant === 'warning') {
		return CircleAlert
	}
	if (props.variant === 'error') {
		return X
	}
})

const iconComponent = computed(() => props.icon || variantIcon.value)

const variantIconClasses = computed(() => {
	if (props.variant === 'success') {
		return 'text-white bg-green-600 p-0.5'
	}
	if (props.variant === 'info') {
		return 'text-white bg-blue-600'
	}
	if (props.variant === 'warning') {
		return 'text-white bg-orange-600'
	}
	if (props.variant === 'error') {
		return 'text-white bg-red-600 p-0.5'
	}
})
</script>
