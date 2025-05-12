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
						<p class="text-p-base font-medium text-gray-900">
							{{ title }}
						</p>
						<p v-if="message" class="text-p-sm text-gray-600">
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

<script setup lang="ts">
import { computed } from 'vue'
import { ToastVariant } from '../helpers/toasts'

const props = defineProps<{
	title: string
	message?: string
	variant: ToastVariant
	icon?: string
	iconClasses?: string
}>()

const containsHTML = computed(() => props.message?.includes('<'))

const variantClasses = computed(() => {
	if (props.variant === 'success') {
		return 'bg-green-50'
	}
	if (props.variant === 'info') {
		return 'bg-blue-50'
	}
	if (props.variant === 'warning') {
		return 'bg-orange-50'
	}
	if (props.variant === 'error') {
		return 'bg-red-50'
	}
})

const variantIcon = computed(() => {
	if (props.variant === 'success') {
		return 'check'
	}
	if (props.variant === 'info') {
		return 'info'
	}
	if (props.variant === 'warning') {
		return 'alert-circle'
	}
	if (props.variant === 'error') {
		return 'x'
	}
})

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
