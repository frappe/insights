import { reactive } from 'vue'

let prompt = reactive({
	show: false,
	options: {},
})

export default function usePrompt() {
	return prompt
}

export function showPrompt(promptOptions) {
	prompt.show = true
	prompt.options = {
		title: promptOptions.title,
		message: promptOptions.message,
		icon: promptOptions.icon,
		actions: [
			{
				...promptOptions.primaryAction,
				label: promptOptions.primaryAction.label,
				handler: promptOptions.primaryAction.action,
			},
			{
				...promptOptions.secondaryAction,
				label: promptOptions.secondaryAction?.label || 'Cancel',
				handler: promptOptions.secondaryAction?.action,
			},
		],
	}
}
