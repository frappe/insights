import { reactive } from 'vue'
import { useRouter } from 'vue-router'

const commandPalette = reactive({
	isOpen: false,
	commands: [],
	open,
	close,
	search,
})

function open() {
	commandPalette.isOpen = true
}
function close() {
	commandPalette.isOpen = false
}
function search(searchTerm) {
	return commandPalette.commands.filter((command) => {
		return command.title.toLowerCase().includes(searchTerm.toLowerCase())
	})
}

function initNavigationCommands(commandPalette) {
	const router = useRouter()
	commandPalette.commands = []
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
		title: 'Data Source',
		description: 'Go to data source list',
		icon: 'arrow-right',
		action: () => {
			router.push('/data-source')
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

export default function useCommandPalette() {
	initNavigationCommands(commandPalette)
	return commandPalette
}
