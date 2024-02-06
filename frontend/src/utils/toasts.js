import Toast from '@/components/Toast.vue'
import { h, markRaw } from 'vue'
import { toast } from 'vue-sonner'

export function createToast(toastOptions) {
	const options = {}
	if (toastOptions.message && toastOptions.title) {
		options.message = toastOptions.message
		options.title = toastOptions.title
	} else if (toastOptions.message && !toastOptions.title) {
		options.message = toastOptions.message
		options.title = titleCase(toastOptions.variant)
	} else if (!toastOptions.message && toastOptions.title) {
		options.message = ''
		options.title = toastOptions.title
	}
	const component = h(Toast, { ...toastOptions, ...options })
	toast(markRaw(component))
}

function titleCase(str) {
	return str
		.toLowerCase()
		.split(' ')
		.map(function (word) {
			return word.charAt(0).toUpperCase() + word.slice(1)
		})
		.join(' ')
}
