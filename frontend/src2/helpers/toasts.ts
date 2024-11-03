import { h, markRaw } from 'vue'
import { toast } from 'vue-sonner'
import Toast from '../components/Toast.vue'
import { titleCase } from './index'

export type ToastVariant = 'success' | 'error' | 'warning' | 'info'
type ToastOptions = {
	title?: string
	message?: string
	variant: ToastVariant
	duration?: number
}
export function createToast(toastOptions: ToastOptions) {
	const options = { ...toastOptions }
	if (!toastOptions.title && toastOptions.message) {
		options.title = titleCase(toastOptions.variant)
		options.message = toastOptions.message
	}
	const component = h(Toast, {
		title: options.title || '',
		message: options.message,
		variant: toastOptions.variant,
	})
	toast.custom(markRaw(component), {
		duration: options.duration || 5000,
	})
}

export function createInfoToast(message: string) {
	createToast({ message, variant: 'info' })
}
export function createSuccessToast(message: string) {
	createToast({ message, variant: 'success' })
}
