import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import frappeui from 'frappe-ui/vite'
import path from 'path'
import { defineConfig } from 'vite'

export default defineConfig({
	plugins: [
		frappeui({
			frappeProxy: true,
			lucideIcons: true,
			jinjaBootData: true,
			buildConfig: false,
		}),
		vue(),
		vueJsx(),
	],
	server: {
		allowedHosts: true,
	},
	esbuild: { loader: 'tsx' },
	resolve: {
		alias: {
			// https://github.com/vitejs/vite/discussions/16730#discussioncomment-13048825
			vue: 'vue/dist/vue.esm-bundler.js',
			'@': path.resolve(__dirname, 'src'),
			'tailwind.config.js': path.resolve(__dirname, 'tailwind.config.js'),
		},
	},
	build: {
		outDir: `../insights/public/frontend`,
		emptyOutDir: true,
		sourcemap: true,
		rollupOptions: {
			input: {
				main: path.resolve(__dirname, 'index.html'),
				insights_v2: path.resolve(__dirname, 'index_v2.html'),
			},
			output: {
				manualChunks: {
					'frappe-ui': ['frappe-ui'],
				},
			},
		},
	},
	optimizeDeps: {
		include: ['feather-icons','showdown','tailwind.config.js','highlight.js/lib/core'],
		
	},
	define: {
		// enable hydration mismatch details in production build
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'true',
	},
})
