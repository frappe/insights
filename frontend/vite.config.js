import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import { getProxyOptions } from 'frappe-ui/src/utils/vite-dev-server'
import path from 'path'
import { defineConfig } from 'vite'
import { webserver_port } from '../../../sites/common_site_config.json'

export default defineConfig({
	plugins: [vue(), vueJsx()],
	esbuild: { loader: 'jsx' },
	server: {
		port: 8080,
		proxy: getProxyOptions({ port: webserver_port }),
	},
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
		},
	},
	build: {
		outDir: `../${path.basename(path.resolve('..'))}/public/frontend`,
		emptyOutDir: true,
		target: 'es2015',
		rollupOptions: {
			output: {
				manualChunks: {
					'frappe-ui': ['frappe-ui'],
				},
			},
		},
	},
	optimizeDeps: {
		include: ['feather-icons', 'showdown', 'engine.io-client'],
	},
})
