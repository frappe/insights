import ConfirmDialog from '../components/ConfirmDialog.vue'
import { VNode, h, ref } from 'vue'

export const dialogs = ref<VNode[]>([])

export function confirmDialog({
	title = 'Untitled',
	message = '',
	primaryActionLabel = 'Confirm',
	theme = 'gray',
	fields = [],
	onSuccess = () => {},
}) {
	const component = h(ConfirmDialog, {
		title,
		message,
		theme,
		fields,
		onSuccess,
		primaryActionLabel,
	})
	dialogs.value.push(component)
}
