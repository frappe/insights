import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import frappeui from 'frappe-ui/vite'
import path from 'path'
import { defineConfig } from 'vite'

export default defineConfig({
	plugins: [
		frappeui({
			source: '^/(app|login|api|assets|files|private)',
		}),
		vue(),
		vueJsx(),
		{
			name: 'transform-index.html',
			transformIndexHtml(html, context) {
				if (!context.server) {
					return html.replace(
						/<\/body>/,
						`
            <script>
                {% for key in boot %}
                window["{{ key }}"] = {{ boot[key] | tojson }};
                {% endfor %}
            </script>
            </body>
            `
					)
				}
				return html
			},
		},
	],
	esbuild: { loader: 'tsx' },
	resolve: {
		alias: {
			'@': path.resolve(__dirname, 'src'),
		},
	},
	build: {
		outDir: `../insights/public/frontend`,
		emptyOutDir: true,
		target: 'es2015',
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
		include: ['feather-icons', 'showdown', 'engine.io-client'],
	},
	define: {
		// enable hydration mismatch details in production build
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'true',
	},
})
