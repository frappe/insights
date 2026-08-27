import { defineConfig, devices } from '@playwright/test'
import { storageStatePath } from './e2e/helpers/auth'

/**
 * The end-to-end suite. `frontend/e2e/AGENTS.md` is the standard it enforces.
 *
 * **What serves the app.** Nothing here starts a server. The suite talks to a
 * running Frappe site that already has Insights installed, the frontend built,
 * and the demo Data Source seeded. There is no `webServer` block because the
 * command that starts a site lives in the bench root, which this package cannot
 * name, and because the site build is the slow part and must be cached across
 * runs. CI starts the site in its own step and polls the port, the same way
 * `frappe/wiki` and `frappe/crm` do.
 *
 * Locally:
 *
 *     cd ~/frappe/develop-bench && bench start
 *     bench --site <site> set-config max_queued_jobs 100000 --parse
 *     cd frontend && yarn build          # /insights needs the built entry
 *     E2E_BASE_URL=http://test.insights.localhost:8000 npx playwright test
 *
 * A vite dev server cannot host this suite. `/insights` under `yarn dev` is
 * vite's own `index.html`, so it carries no `window.csrf_token` and the setup
 * project fails. Point the suite at the bench port, not at vite.
 *
 * **Why `max_queued_jobs` is not optional.** A full run enqueues about 300
 * background jobs, mostly link cleanup behind the Workbook deletes the fixtures
 * make. One `bench worker` drains about two a second, so the queue grows by
 * about 190 jobs a run and never empties between runs. Once it passes
 * `max_queued_jobs`, which is 500 plus 50 per site on the bench, Frappe answers
 * every write that enqueues a job with a 503 `QueueOverloaded`. That reddened
 * 17 of 54 tests in one measured run, across four spec files at once. The jobs
 * are cleanup the suite never reads, so a deep queue costs it nothing.
 */
const baseURL = process.env.E2E_BASE_URL || 'http://test.insights.localhost:8000'

/**
 * Quarantined tests are excluded from every run by default, so a flaky test
 * cannot redden the merge gate while its 7-day window runs. Set
 * `E2E_QUARANTINE=1` to include them, and add `--grep @quarantine` to run only
 * them.
 */
const excludeQuarantined = process.env.E2E_QUARANTINE ? undefined : /@quarantine/

export default defineConfig({
	testDir: './e2e/tests',
	fullyParallel: true,
	grepInvert: excludeQuarantined,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	// Three workers, everywhere. Playwright's local default is half the cores,
	// which is five on the machine this was measured on, and five loses about
	// one chart flow a run.
	//
	// The reason is ticket 18. A chart page saves itself about every 1.5
	// seconds, for as long as it is open, and each save answer replaces the
	// whole document, so a click made while a save is in flight is dropped. The
	// odds of landing in that window scale with the round trip, and the round
	// trip scales with how many workers share the one Frappe site. No ordering
	// of clicks escapes it, because there is always a save in flight.
	//
	// Measured over seven full runs each: five workers 56, 55, 55, 56, 55, 55,
	// 55 in 60 seconds; three workers 56 every run in 77. Sixteen seconds buys
	// the gate.
	workers: 3,
	reporter: process.env.CI
		? [['github'], ['html', { open: 'never' }]]
		: [['list'], ['html', { open: 'never' }]],
	// A flow that runs a query waits on DuckDB and on ibis compilation, so the
	// generator default of 30 seconds is too tight for an author flow.
	timeout: 90_000,
	expect: {
		// Playwright's 5 second default expires while a first query execution is
		// still running. Raise a single assertion above this where the flow needs
		// it, rather than raising this further.
		timeout: 15_000,
	},
	use: {
		baseURL,
		trace: 'on-first-retry',
		video: 'retain-on-failure',
		screenshot: 'only-on-failure',
	},

	projects: [
		{
			// Logs both roles in, creates the viewer, and seeds the demo Data
			// Source. Every other project depends on it, so it runs first and once.
			name: 'setup',
			testMatch: /.*\.setup\.ts/,
		},
		{
			name: 'chromium',
			dependencies: ['setup'],
			testIgnore: /.*\.setup\.ts/,
			use: {
				...devices['Desktop Chrome'],
				// The `page` fixture is the admin. `viewerPage` opens its own
				// context from the viewer's saved state.
				storageState: storageStatePath('admin'),
			},
		},
	],
})
