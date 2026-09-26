// An entry name is the island's name. The preset writes it into assets.json as
// `<name>.island.js`, and every host finds the island by that name. Renaming an
// entry breaks every host that uses it.

import { buildIslands } from '@framework/ui/vite/island'

await buildIslands({
	app: 'insights',
	root: import.meta.dirname,
	entries: {
		'insights.chart': 'src2/islands/chart.ts',
		'insights.dashboard': 'src2/islands/dashboard.ts',
	},
	// No content list: the preset scans the modules each island is built from, so
	// a helper with class literals cannot be left out of the scan.

	// The SPA's plugin. Without it the Number grid's `@xl:` columns compile to nothing.
	tailwindPlugins: ['@tailwindcss/container-queries'],
	// Set just above the current build. An island that renders the full dashboard
	// bundles its own Vue, frappe-ui, the chart library and the app's stylesheet,
	// about 1.72 MB.
	budget: 1800 * 1024,
	// The budget catches these imports late and only by size. Each one pulls in
	// something a reader cannot use: routed pages, the builder's stores, or a
	// resource load that needs a role. They are checked after vite removes types,
	// so `import type` from them still passes.
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
