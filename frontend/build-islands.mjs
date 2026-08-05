// Builds Insights' islands: a second target beside the SPA's `yarn build`, same
// source tree, different output contract. The preset registers the
// `<name>.island.js` keys that hooks.py's `ui_islands` points at.

import { buildIslands } from '@framework/ui/vite/island'

await buildIslands({
	app: 'insights',
	root: import.meta.dirname,
	entries: {
		insights_chart: 'src2/islands/chart.ts',
	},
	// Only the modules an island renders: the builder's forms and dialogs would
	// otherwise ship their utilities in every island sheet.
	content: [
		'src2/islands/**/*.{vue,ts}',
		'src2/components/**/*.vue',
		'src2/charts/components/{BaseChart,ChartBody,ChartSectionEmptySvg,ChartTitle,NumberChart,Sparkline,TableChart}.vue',
		'src2/query/components/{QueryDataTable,AlertSetupDialog,QueryAlertsDialog,ExpressionEditor}.vue',
	],
	// The size budget catches a recoupled entry late and by weight. These two
	// name the recouplings we already paid for: the SPA router (every routed
	// page) and the workbook store (the whole builder aggregate).
	forbiddenImports: [/\/router(\.ts)?$/, /\/workbook\/workbook(\.ts)?$/],
	production: process.argv.includes('--production'),
	watch: process.argv.includes('--watch'),
})
