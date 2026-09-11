import { toast } from 'frappe-ui'
import { waitUntil, wheneverChanges } from '../helpers'
import router from '../router'
import { __ } from '../translation'
import useWorkbook from './workbook'

// What a query, chart or dashboard does *because* it sits in a workbook. It
// lives here so the item stores stay free of the workbook store: a chart or a
// dashboard is read on surfaces that have no workbook and no builder around
// them.

type WorkbookItemType = 'query' | 'chart' | 'dashboard'

type WorkbookItem = {
	isloaded: boolean
	doc: { name: string; title: string; workbook: string }
	call: (method: string) => Promise<any>
}

const listOf = {
	query: 'queries',
	chart: 'charts',
	dashboard: 'dashboards',
} as const

// Item stores are cached for the session, so a mirror outlives the page that
// asked for it — opening the same item again must not stack a second one.
const mirrored = new WeakSet<WorkbookItem>()

/** Keep the workbook's item list showing the item's current title. */
export function mirrorTitleToWorkbook(item: WorkbookItem, type: WorkbookItemType) {
	if (mirrored.has(item)) return
	mirrored.add(item)

	waitUntil(() => item.isloaded).then(() => {
		wheneverChanges(
			() => item.doc.title,
			() => {
				if (!item.doc.workbook) return
				const workbook = useWorkbook(item.doc.workbook)
				for (const entry of workbook.doc[listOf[type]]) {
					if (entry.name === item.doc.name) {
						entry.title = item.doc.title
						break
					}
				}
			},
			{ debounce: 500 },
		)
	})
}

/** Copy the item inside its workbook and open the copy. */
export function duplicateWorkbookItem(item: WorkbookItem, type: 'query' | 'chart') {
	const workbook = useWorkbook(item.doc.workbook)
	return item
		.call('duplicate')
		.then((newName: string) => {
			toast.success(type === 'chart' ? __('Chart duplicated') : __('Query duplicated'))
			router.push(`/workbook/${item.doc.workbook}/${type}/${newName}`)
		})
		.then(workbook.load)
}
