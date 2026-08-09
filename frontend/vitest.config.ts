import vue from '@vitejs/plugin-vue'
import { lucideIcons } from 'frappe-ui/vite'
import { defineConfig } from 'vitest/config'

// Deliberately not `vite.config.js`: that one starts a proxy to the bench site
// and reads boot data, which a unit test has no use for. What is left is what a
// pure function needs — a resolver, the SFC compiler because the adapter names
// the chart components it returns, and frappe-ui's icon resolver because its
// components reach for `~icons/lucide/*`.
export default defineConfig({
	plugins: [vue(), lucideIcons()],
	resolve: {
		// frappe-ui is linked from the framework checkout and carries its own
		// node_modules, so anything with a single-instance contract has to
		// resolve to this app's copy. Same reason as `vite.config.js`.
		// `@vueuse/core` is here for a second reason. reka-ui asks for v14, and
		// the frappe-ui checkout installed that v14 core with no `@vueuse/shared`
		// beside it — so it reaches the v10 shared hoisted above it and fails on
		// `createRef`. Deduping sends every core to this app's v10, which has its
		// own matching shared. `vite.config.js` has done this all along, which is
		// why the build never saw the break.
		dedupe: ['vue', 'echarts', '@vueuse/core'],
	},
	test: {
		include: ['src2/**/*.test.ts'],
		environment: 'node',
		server: {
			// A dependency Vitest externalizes is loaded by Node, and Node resolves
			// it from its own directory — which puts `dedupe` above out of reach.
			// Inlining these two hands them back to Vite, so the rule applies.
			deps: { inline: [/@vueuse\//, /reka-ui/] },
		},
	},
})
