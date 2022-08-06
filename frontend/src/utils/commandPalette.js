import { reactive } from 'vue'
import { useRouter } from 'vue-router'

export default function useCommandPalette() {
	const commandPalette = reactive({
		commands: [],
		search,
	})
	function search(searchTerm) {
		return commandPalette.commands.filter((command) => {
			return command.title.toLowerCase().includes(searchTerm.toLowerCase())
		})
	}

	initNavigationCommands(commandPalette)

	return commandPalette
}

function initNavigationCommands(commandPalette) {
	const router = useRouter()
	commandPalette.commands.push({
		title: 'Query',
		description: 'Go to query list',
		icon: 'arrow-right',
		action: () => {
			router.push('/query')
		},
	})
	commandPalette.commands.push({
		title: 'Dashboard',
		description: 'Go to dashboard list',
		icon: 'arrow-right',
		action: () => {
			router.push('/dashboard')
		},
	})
	commandPalette.commands.push({
		title: 'Settings',
		description: 'Go to settings',
		icon: 'arrow-right',
		action: () => {
			router.push('/settings')
		},
	})
}
