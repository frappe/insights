import { call, useColorScheme } from 'frappe-ui'
import { HelpCircle, LogOut, MessageCircle, Moon, Sun, ToggleRight } from 'lucide-vue-next'
import { computed, h, ref } from 'vue'
import { showErrorToast } from '../helpers'
import { confirmDialog } from '../helpers/confirm_dialog'
import session from '../session'
import FrappeCloudIcon from './Icons/FrappeCloudIcon.vue'
import { __ } from '../translation'

declare global {
	interface Window {
		is_fc_site?: boolean
	}
}

// whether the site runs on Frappe Cloud, which adds its login and trial banner
export const isFCSite = Boolean(window.is_fc_site)

// The user menu, for the sidebar's dropdown and the phone's You sheet. The
// Frappe Cloud dialog is one: the sidebar renders it, and both open it.
export const showLoginToFCDialog = ref(false)

export function useUserMenuOptions() {
	const { colorScheme, toggleColorScheme } = useColorScheme()
	const isDark = computed(() => colorScheme.value === 'dark')

	const userDropdownOptions = computed(() => {
		const options: { label: string; icon: any; onClick: () => void }[] = [
			{
				label: __('Documentation'),
				icon: h(HelpCircle),
				onClick: () => window.open('https://docs.frappe.io/insights', '_blank'),
			},
			{
				label: __('Join Telegram Group'),
				icon: h(MessageCircle),
				onClick: () => window.open('https://t.me/frappeinsights', '_blank'),
			},
		]

		if (session.user.is_admin || session.user.has_desk_access) {
			options.push({
				label: __('Switch to Desk'),
				icon: h(ToggleRight),
				onClick: () => window.open('/app', '_blank'),
			})
		}
		if (isFCSite) {
			options.push({
				icon: h(FrappeCloudIcon),
				label: __('Login to Frappe Cloud'),
				onClick: () => (showLoginToFCDialog.value = true),
			})
		}

		options.push({
			label: isDark.value ? __('Light mode') : __('Dark mode'),
			icon: h(isDark.value ? Sun : Moon),
			onClick: toggleColorScheme,
		})
		options.push({
			label: __('Log out'),
			icon: h(LogOut),
			onClick: () =>
				confirmDialog({
					title: __('Log out'),
					message: __('Are you sure you want to log out?'),
					onSuccess: session.logout,
				}),
		})

		return options
	})

	return userDropdownOptions
}

export const loggingInToFC = ref(false)
export function loginToFC() {
	loggingInToFC.value = true
	call('frappe.integrations.frappe_providers.frappecloud_billing.current_site_info')
		.then((data: any) => {
			if (!data.base_url || !data.site_name) {
				throw new Error('Invalid response')
			}
			window.open(`${data.base_url}/dashboard/sites/${data.site_name}`, '_blank')
		})
		.catch(showErrorToast)
		.finally(() => {
			loggingInToFC.value = false
		})
}
