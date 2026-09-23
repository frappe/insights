// Builds Insights' islands: a second target beside the SPA's `yarn build`, same
// source tree, different output contract. An entry name is the island's name:
// the preset writes it into assets.json as `<name>.island.js`, which is the
// registry every placement resolves against, so renaming one here breaks every
// host that names it.

import { buildIslands } from '@framework/ui/vite/island'

await buildIslands({
	app: 'insights',
	root: import.meta.dirname,
	entries: {
		'insights.chart': 'src2/islands/chart.ts',
		'insights.dashboard': 'src2/islands/dashboard.ts',
	},
	// No content list: the preset scans the modules each island is built from, so
	// a helper holding class literals cannot be left out of the scan by accident.

	// The SPA's plugin. Without it the Number grid's `@xl:` columns compile to nothing.
	tailwindPlugins: ['@tailwindcss/container-queries'],
	// Pinned just over the current clean build: an island that draws the real
	// dashboard carries its own Vue, frappe-ui, the charting engine and the app's
	// stylesheet, and that is 1.72 MB of it.
	budget: 1800 * 1024,
	// The budget catches a recoupled entry late and by weight; these name the
	// recouplings. Each drags something a reader cannot do: routed pages, the
	// builder aggregate, or a role-gated resource load. Checked after vite erases
	// types, so `import type` from any of them still passes.
	forbiddenImports: [
		/\/router(\.ts)?$/,
		/\/workbook\/workbook(\.ts)?$/,
		/\/charts\/chart(\.ts)?$/,
		/\/query\/query(\.ts)?$/,
		/\/dashboard\/dashboard(\.ts)?$/,
		// Desk holds the page's socket. An island that opened its own would
		// bundle a second 40 kB client and a second connection with it.
		/^socket\.io-client$/,
	],
	production: process.argv.includes('--production'),
	watch: process.argv.includes('--watch'),
})
