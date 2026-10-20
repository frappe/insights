import { translatedTable, __ } from '../translation'
import type { UpgradeItem } from './upgrade'

export type AttentionGroup = {
	code: string
	title: string
	/** Why these items changed and what to do, said once for the group. */
	description: string
	items: UpgradeItem[]
}

type GroupText = Pick<AttentionGroup, 'title' | 'description'>

// In the order an admin should work through them: who sees which data first,
// then what stops working, then what shows other numbers, then cleanup.
const groupText = translatedTable<Record<string, GroupText>>(() => ({
	P17: {
		title: __('Site data now follows desk permissions'),
		description: __(
			'Team access and Table Restrictions no longer apply to site data. Give each user the desk roles or User Permissions that match what they should see.',
		),
	},
	P10: {
		title: __("Public charts now show their owner's rows"),
		description: __(
			'These rows depend on who reads them, and signed-in readers saw their own in Insights 3. To show them their own again, stop sharing the chart and its dashboards publicly, then turn off Run as owner.',
		),
	},
	P7: {
		title: __('Workbooks shared in place of their charts'),
		description: __(
			'Insights 4 shares whole workbooks, not what is in them, and removed shares with everyone. Unshare anyone who should not see the whole workbook.',
		),
	},
	P3: {
		title: __('Workbooks shared with the people who built in them'),
		description: __(
			'Only the workbook gives access now. Unshare anyone who should not edit the whole workbook.',
		),
	},
	P11: {
		title: __('Public charts moved to their publisher'),
		description: __(
			'A public chart runs as its owner now, so it moved to the user who published it and shows the rows it showed before. If that user is disabled, turn on Run as owner in its share dialog.',
		),
	},
	P12: {
		title: __("Public charts that can't run as their owner"),
		description: __(
			'Until the owner can edit the chart again, it runs as each reader and guests see nothing. Enable the owner, give them an Insights role, or share the workbook with them to edit.',
		),
	},
	P19: {
		title: __('Alerts that run as someone else or will stop'),
		description: __(
			'An alert runs as a user who can edit its workbook. Share the workbook with the user who turned it on, or turn it off and on again as an editor.',
		),
	},
	Q1: {
		title: __('Scripts that will fail'),
		description: __('Scripts run in a narrower sandbox. Remove the names listed.'),
	},
	J4: {
		title: __('Import jobs that will fail'),
		description: __(
			'Scripts run in a narrower sandbox, and a failing job stops syncing its table. Remove the names listed.',
		),
	},
	Q5: {
		title: __('Expressions that reach the database'),
		description: __(
			'Insights 4 refuses these calls. Remove the call, or ask an admin to make it a script query.',
		),
	},
	P21: {
		title: __('Queries copied from another workbook'),
		description: __(
			'A query reads only its own workbook now, so the queries it read were copied in. Each copy runs once you fix what is listed.',
		),
	},
	C4: {
		title: __('Reference lines that moved'),
		description: __(
			'A line at an average or other statistic now reads one series, and needs a measure. Check where it lands.',
		),
	},
	N6: {
		title: __('Number cards that lost their period'),
		description: __(
			'Insights 4 cannot group by time of day, so these show the total of all rows. Pick a Date or Datetime column to show a period.',
		),
	},
	P4: {
		title: __('Team members who can no longer edit'),
		description: __(
			'A team gives read access only. To let them edit, share the workbook with them as editors.',
		),
	},
	P20: {
		title: __('Code only admins can change now'),
		description: __(
			'Scripts, expressions that run SQL and stored procedure calls still run. To let the author edit them, add them to the Admin team.',
		),
	},
	N5: {
		title: __('Number cards that show a day now'),
		description: __(
			'Insights 3 showed the value at the latest date and time. These show the total of the latest day.',
		),
	},
	N4: {
		title: __('Number cards that lost their currency symbol'),
		description: __(
			'The suffix now takes the place of a symbol that goes after the number. Add the symbol to the suffix to show it again.',
		),
	},
	K1: {
		title: __('Date filter defaults removed'),
		description: __(
			'Insights 3 showed these defaults but never applied them, so the dashboards showed every date. Set one again to apply it.',
		),
	},
	Q13: {
		title: __('Fiscal Year Start is blank'),
		description: __(
			'Insights 3 started fiscal years on 1 April in date filters and on 1 January in fiscal-year groups. Set Fiscal Year Start to choose the date.',
		),
	},
	J1: {
		title: __('Alerts on a chart check a copy of its data'),
		description: __(
			'Changes to the chart no longer reach the alert. Open the query to change what it checks.',
		),
	},
	W2: {
		title: __('Copies of Insights 3 templates'),
		description: __(
			'A standard workbook replaces each and gets the updates. Delete a copy nobody changed.',
		),
	},
}))

/** The items grouped by code, most important first. A code with no text
 * comes last, and its items speak for themselves. */
export function attentionGroups(items: UpgradeItem[]): AttentionGroup[] {
	const text = groupText()
	const order = Object.keys(text)
	const byCode = new Map<string, UpgradeItem[]>()
	for (const item of items) {
		byCode.set(item.code, [...(byCode.get(item.code) ?? []), item])
	}
	const rank = (code: string) => (code in text ? order.indexOf(code) : order.length)
	return [...byCode.entries()]
		.sort(([a], [b]) => rank(a) - rank(b))
		.map(([code, items]) => ({
			code,
			title: text[code]?.title ?? __('Other changes'),
			description: text[code]?.description ?? '',
			items,
		}))
}
