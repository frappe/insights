import { call } from 'frappe-ui'
import { reactive } from 'vue'
import { showErrorToast } from '../helpers'
import session from '../session'

export type UpgradeTab = 'whats_new' | 'attention'

export type UpgradeItem = {
	name: string
	code: string
	message: string
	reference_doctype: string | null
	reference_name: string | null
	user: string | null
	action: '' | 'delete_workbook' | 'open_settings' | null
	/** The workbook the reference is opened in, if it has a route in the app. */
	workbook: string | null
	/** The desk form of a reference the app has no page for, such as a user. */
	form_url: string | null
	/** Whether the user holds the permission the fix needs. */
	can_fix: boolean
}

const upgrade = reactive({
	show: false,
	tab: 'whats_new' as UpgradeTab,
	items: [] as UpgradeItem[],
	open,
	close,
	dismiss,
	fix,
})

async function loadItems() {
	upgrade.items = await call('insights.api.upgrade.get_upgrade_items')
	session.user.upgrade_item_count = upgrade.items.length
}

function open(tab: UpgradeTab) {
	upgrade.tab = tab
	upgrade.show = true
	return loadItems().catch((error) => showErrorToast(error, false))
}

async function close() {
	upgrade.show = false
	if (!session.user.upgraded_from_v3) return
	session.user.upgraded_from_v3 = false
	await call('insights.api.upgrade.mark_upgrade_seen').catch((error) =>
		showErrorToast(error, false),
	)
}

function dismiss(item: UpgradeItem) {
	return resolve(item, 'insights.api.upgrade.dismiss_upgrade_item')
}

function fix(item: UpgradeItem) {
	return resolve(item, 'insights.api.upgrade.fix_upgrade_item')
}

async function resolve(item: UpgradeItem, method: string) {
	try {
		await call(method, { name: item.name })
	} catch (error: any) {
		showErrorToast(error, false)
		return
	}
	upgrade.items = upgrade.items.filter((i) => i.name !== item.name)
	session.user.upgrade_item_count = upgrade.items.length
}

export default upgrade
