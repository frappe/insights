import { Book, Database, DatabaseZap, LayoutGrid, SettingsIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import session from '../session'
import useSettings from '../settings/settings'
import { __ } from '../translation'

// The sidebar renders the Settings dialog, and the phone's You sheet opens it too
export const showSettingsDialog = ref(false)

// The app's places, for the sidebar and the phone's tab bar alike
export function useNavLinks() {
	// A reader without an Insights role reads dashboards and nothing else, so the
	// rest is neither shown nor fetched
	const builder = session.isAuthorized
	const settings = builder ? useSettings() : undefined

	return ref([
		{
			label: __('Dashboards'),
			icon: LayoutGrid,
			to: 'DashboardList',
		},
		{
			label: __('Workbooks'),
			icon: Book,
			to: 'WorkbookList',
			hidden: !builder,
		},
		{
			label: __('Data Sources'),
			icon: Database,
			to: 'DataSourceList',
			hidden: !builder,
		},
		{
			label: __('Data Store'),
			icon: DatabaseZap,
			to: 'DataStoreList',
			hidden: computed(() => !settings?.doc.enable_data_store),
		},
		{
			label: __('Settings'),
			icon: SettingsIcon,
			onClick: () => (showSettingsDialog.value = true),
			hidden: !builder,
		},
	])
}
