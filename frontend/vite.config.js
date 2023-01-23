import path from 'path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import istanbul from 'vite-plugin-istanbul'
import { getProxyOptions } from 'frappe-ui/src/utils/vite-dev-server'
import { webserver_port } from '../../../sites/common_site_config.json'

export default defineConfig({
	plugins: [
		vue(),
		// istanbul({
		// 	include: 'src/*',
		// 	exclude: ['node_modules', 'src/test/'],
		// 	extension: ['.js', '.vue'],
		// 	forceBuildInstrument: true,
		// }),
	],
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
		sourcemap: true,
	},
	optimizeDeps: {
		include: ['feather-icons', 'showdown', 'engine.io-client'],
	},
})
