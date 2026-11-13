import { call, toast } from 'frappe-ui'
import router from '../router'
import session from '../session'
import { __ } from '../translation'

/** Set up the demo data and open the sample workbook it brings. */
export async function setupDemoData() {
	try {
		const workbook: string | null = await call('insights.setup.setup_wizard.setup_demo_data')
		session.user.has_demo_data = true
		toast.success(__('Demo Data Ready'), {
			description: __('Sample data and a workbook built on it are ready'),
		})
		if (workbook) router.push(`/workbook/${workbook}`)
	} catch {
		toast.error(__('Setup Failed'), {
			description: __('Failed to setup demo data'),
		})
	}
}
