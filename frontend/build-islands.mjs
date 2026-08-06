// Builds Insights' islands: a second target beside the SPA's `yarn build`, same
// source tree, different output contract. The preset registers the
// `<name>.island.js` keys that hooks.py's `ui_islands` points at.

import { buildIslands } from '@framework/ui/vite/island'

await buildIslands({
	app: 'insights',
	root: import.meta.dirname,
	entries: {
		insights_chart: 'src2/islands/chart.ts',
		insights_dashboard: 'src2/islands/dashboard.ts',
	},
	// Only the modules an island renders: the builder's forms and dialogs would
	// otherwise ship their utilities in every island sheet.
	content: [
		'src2/islands/**/*.{vue,ts}',
		'src2/components/**/*.vue',
		'src2/charts/components/{BaseChart,ChartBody,ChartSectionEmptySvg,ChartTitle,NumberChart,Sparkline,TableChart}.vue',
		'src2/query/components/{ColumnFilterValueSelector,DataTypeIcon,NumberFilterPicker,QueryDataTable,RelativeDatePicker}.vue',
		'src2/dashboard/{Filter,FilterControl,VueGridLayout}.vue',
	],
	// The SPA's plugin. Without it NumberChart's `@xl:` columns compile to nothing.
	tailwindPlugins: ['@tailwindcss/container-queries'],
	// 18 kB of typography the runtime sheet already carries — the shadow root
	// adopts both, runtime first, so text items render off that copy.
	blocklist: ['prose', 'prose-v3'],
	// Pinned from the measured dashboard build plus slack, so it bites when an
	// entry picks up a graph it has no business in.
	budget: 152 * 1024,
	// The budget catches a recoupled entry late and by weight; these name the
	// recouplings. Each drags something a viewer cannot do: routed pages, the
	// builder aggregate, or a role-gated resource load. Checked after vite erases
	// types, so `import type` from any of them still passes.
	forbiddenImports: [
		/\/router(\.ts)?$/,
		/\/workbook\/workbook(\.ts)?$/,
		/\/charts\/chart(\.ts)?$/,
		/\/query\/query(\.ts)?$/,
		/\/dashboard\/dashboard(\.ts)?$/,
	],
	production: process.argv.includes('--production'),
	watch: process.argv.includes('--watch'),
})
