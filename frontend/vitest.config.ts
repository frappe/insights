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
		dedupe: ['vue', 'echarts'],
	},
	test: {
		include: ['src2/**/*.test.ts'],
		environment: 'node',
	},
})
