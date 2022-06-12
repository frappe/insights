import { h, reactive, ref } from 'vue'
import Toast from '@/components/Toast.vue'

let toasts = ref([])

export default {
	name: 'Toasts',
	render() {
		return toasts.value.map((toast) => h(Toast, toast))
	},
}

export function createToast(toastOptions) {
	let toast = reactive({
		key: 'toast-' + toasts.value.length,
		...toastOptions,
	})
	toasts.value.push(toast)
}
