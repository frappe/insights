import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import frappeui from 'frappe-ui/vite'
import fs from 'node:fs'
import path from 'path'
import { defineConfig, searchForWorkspaceRoot } from 'vite'

// The real directory behind the frappe-ui link, which lives in the framework
// checkout — outside this app. The dev server refuses to serve files from
// there unless told, and the only ones it is asked for are the Inter woff2s.
const frappeUIRoot = fs.realpathSync(path.resolve(__dirname, 'node_modules/frappe-ui'))

// Pre-bundled below to avoid a dev-only duplicate prosemirror-state instance
// (TipTap "keyed plugin" error). Keep in sync with frappe-ui's @tiptap/* deps.
// frappe-ui is a link dependency, so each id is resolved through it — otherwise
// we would pre-bundle the hoisted copy while frappe-ui uses its own.
const tiptapDeps = [
	'@tiptap/core',
	'@tiptap/vue-3',
	'@tiptap/starter-kit',
	'@tiptap/suggestion',
	'@tiptap/markdown',
	'@tiptap/extensions',
	'@tiptap/extension-blockquote',
	'@tiptap/extension-bold',
	'@tiptap/extension-bubble-menu',
	'@tiptap/extension-code',
	'@tiptap/extension-code-block',
	'@tiptap/extension-code-block-lowlight',
	'@tiptap/extension-color',
	'@tiptap/extension-document',
	'@tiptap/extension-hard-break',
	'@tiptap/extension-heading',
	'@tiptap/extension-highlight',
	'@tiptap/extension-horizontal-rule',
	'@tiptap/extension-image',
	'@tiptap/extension-italic',
	'@tiptap/extension-link',
	'@tiptap/extension-list',
	'@tiptap/extension-mention',
	'@tiptap/extension-node-range',
	'@tiptap/extension-paragraph',
	'@tiptap/extension-placeholder',
	'@tiptap/extension-strike',
	'@tiptap/extension-table',
	'@tiptap/extension-task-item',
	'@tiptap/extension-task-list',
	'@tiptap/extension-text',
	'@tiptap/extension-text-align',
	'@tiptap/extension-text-style',
	'@tiptap/extension-typography',
	'@tiptap/extension-underline',
	// @tiptap/pm exposes only subpaths
	'@tiptap/pm/state',
	'@tiptap/pm/view',
	'@tiptap/pm/model',
	'@tiptap/pm/tables',
].map((dep) => `frappe-ui > ${dep}`)

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
		fs: {
			// Without this the font 403s, Inter never loads, and every screen
			// silently falls back to system sans — in dev only, because the
			// build copies the woff2 into its own assets.
			allow: [searchForWorkspaceRoot(process.cwd()), frappeUIRoot],
		},
	},
	esbuild: { loader: 'ts' },
	resolve: {
		// frappe-ui is linked from the framework checkout (framework's lockfile
		// is the version authority) and carries its own node_modules, so
		// anything with a single-instance contract has to resolve to this app's
		// copy. The link — and this list — go once that frappe-ui publishes.
		dedupe: ['vue', 'vue-router', '@headlessui/vue', '@vueuse/core', 'dayjs'],
		alias: {
			// https://github.com/vitejs/vite/discussions/16730#discussioncomment-13048825
			vue: 'vue/dist/vue.esm-bundler.js',
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
			},
			output: {
				manualChunks: {
					'frappe-ui': ['frappe-ui'],
				},
			},
		},
	},
	optimizeDeps: {
		esbuildOptions: {
			loader: {
				'.ts': 'ts',
				'.tsx': 'tsx',
			},
		},
		include: [
			'feather-icons',
			'tailwind.config.js',
			'highlight.js/lib/core',
			'echarts/core',
			...tiptapDeps,
		],
		exclude: ['frappe-ui'],
	},
	define: {
		// enable hydration mismatch details in production build
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'true',
	},
})
