import { expect, test } from '../fixtures'
import { INSIGHTS_PATH, VIEWER_EMAIL } from '../helpers/auth'
import {
	createWorkbook,
	deleteTeam,
	deleteWorkbook,
	shareWorkbook,
	uniqueTitle,
} from '../helpers/insights'

test.describe('permissions', () => {
	test('a viewer sees only the workbooks granted to them', async ({ adminApi, viewerPage }) => {
		// Both titles carry one marker, so the list search reaches this pair and
		// nothing else. Other agents seed workbooks into the same site, so a count
		// over the whole list would prove nothing.
		const marker = uniqueTitle('Visibility')
		const granted = await createWorkbook(adminApi, `${marker} granted`)
		const hidden = await createWorkbook(adminApi, `${marker} hidden`)
		await shareWorkbook(adminApi, granted.name, [{ user: VIEWER_EMAIL, access: 'view' }])

		await viewerPage.goto(`${INSIGHTS_PATH}/workbook`)
		await viewerPage.getByPlaceholder('Search by title').fill(marker)

		await expect(viewerPage.getByText(granted.title)).toBeVisible()
		await expect(viewerPage.getByText(hidden.title)).toHaveCount(0)

		await deleteWorkbook(adminApi, granted.name)
		await deleteWorkbook(adminApi, hidden.name)
	})

	test('a viewer cannot edit a workbook they can read', async ({
		adminApi,
		demoDataSource,
		viewerPage,
		workbookWithQuery,
	}) => {
		const { workbook, query } = workbookWithQuery
		await shareWorkbook(adminApi, workbook.name, [{ user: VIEWER_EMAIL, access: 'view' }])

		await viewerPage.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}/query/${query.name}`)
		await expect(viewerPage.getByRole('link', { name: query.title })).toBeVisible()

		// locator: the read-only marker is a bare lucide icon in the navbar. It
		// carries no role, no label and no text, so the class lucide stamps on
		// every icon it draws is the only name this element has.
		const readOnlyMarker = viewerPage.locator('.lucide-shield-alert')
		await expect(readOnlyMarker).toBeVisible()
		await readOnlyMarker.hover()
		// The bubble is rendered twice: the copy a reader sees, and an aria-hidden
		// mirror that names the trigger for a screen reader. The visible one comes
		// first, and neither carries a role that tells them apart.
		await expect(
			viewerPage.getByText('You have read-only access to this workbook').first(),
		).toBeVisible()

		// Sharing belongs to the owner, so a granted reader gets no Share button.
		await expect(viewerPage.getByRole('button', { name: 'Share' })).toHaveCount(0)
	})

	test('an admin creates a team and grants a resource', async ({
		page,
		adminApi,
		demoDataSource,
	}) => {
		const teamName = uniqueTitle('Team')
		await page.goto(`${INSIGHTS_PATH}/workbook`)

		// The sidebar entries and the settings tabs are divs carrying their label,
		// not buttons, so the text is the first rung of the ladder that reaches
		// them. Each name is unique until its own panel renders the same heading.
		await page.getByText('Settings', { exact: true }).click()
		await page.getByText('Permissions', { exact: true }).click()

		await page.getByRole('button', { name: 'New Team' }).click()
		await page.getByLabel('Team Name').fill(teamName)
		await page.getByRole('button', { name: 'Create' }).click()
		await expect(page.getByText(teamName)).toBeVisible()

		await page.getByText(teamName).click()
		// The tabs inside the dialog are a frappe-ui TabButtons, which renders a
		// radio group and not buttons.
		await page.getByRole('radio', { name: 'Access' }).click()

		// locator: a resource row has no role, and its Data Source title appears
		// elsewhere on the page. `data-source` names one row exactly. A row holds
		// one checkbox while it stays collapsed.
		const demoRow = page.locator(`[data-source="${demoDataSource}"]`)
		await demoRow.getByRole('checkbox').check()
		await page.getByRole('button', { name: 'Done' }).click()
		await expect(page.getByText('Team updated')).toBeVisible()

		// Reopen the team. A grant that survives a reload is a grant that saved.
		await page.getByText(teamName).click()
		await page.getByRole('radio', { name: 'Access' }).click()
		await expect(demoRow.getByRole('checkbox')).toBeChecked()

		await deleteTeam(adminApi, teamName)
	})

	test('a user without data source access cannot query it', async ({
		adminApi,
		demoDataSource,
		viewerPage,
		workbook,
	}) => {
		await shareWorkbook(adminApi, workbook.name, [{ user: VIEWER_EMAIL, access: 'edit' }])

		// Team permissions are on for the whole run, and the viewer belongs to no
		// team. The setup project sets the switch, because a test that flipped it
		// would flip it for every worker beside it.
		await viewerPage.goto(`${INSIGHTS_PATH}/workbook/${workbook.name}`)

		// The three interface cards are clickable divs with no role and no
		// label, so getByText is the first rung that reaches them.
		await viewerPage.getByText('Query Builder').click()

		await expect(viewerPage.getByText('Pick Starting Data')).toBeVisible()
		await expect(
			viewerPage.getByRole('button', { name: `orders ${demoDataSource}` }),
		).toHaveCount(0)
		await expect(viewerPage.getByRole('button', { name: 'Confirm' })).toBeDisabled()
	})
})
