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
				label: promptOptions.primaryAction.label,
				appearance: promptOptions.primaryAction.appearance,
				handler: () => {
					prompt.show = false
					promptOptions.primaryAction.action()
				},
			},
			{
				label: promptOptions.secondaryAction?.label || 'Cancel',
				appearance: promptOptions.secondaryAction?.appearance,
				handler: () => {
					prompt.show = false
					promptOptions.secondaryAction?.action()
				},
			},
		],
	}
}
