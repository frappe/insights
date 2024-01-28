import { toast } from 'vue-sonner'

export function createToast(toastOptions) {
	const { title, variant, message } = toastOptions
	const variantToFnMap = {
		info: toast.info,
		error: toast.error,
		warning: toast.warning,
		success: toast.success,
	}
	const toastFn = variantToFnMap[variant]
	toastFn(message || title)
}
