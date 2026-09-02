import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import fs from 'fs'
import frappeui from 'frappe-ui/vite'
import path from 'path'
import { defineConfig, searchForWorkspaceRoot } from 'vite'

// The real directory `frappe-ui` resolves to. The dev server serves only what
// its allow-list covers, and the files it is asked for from there are the Inter
// woff2s. A no-op while the package sits inside the workspace.
const frappeUIRoot = fs.realpathSync(path.resolve(__dirname, 'node_modules/frappe-ui'))

const echartsEntries = [
	'echarts/core',
	'echarts/charts',
	'echarts/components',
	'echarts/renderers',
	'echarts/features',
]

// Pre-bundled below to avoid a dev-only duplicate prosemirror-state instance
// (TipTap "keyed plugin" error). Keep in sync with frappe-ui's @tiptap/* deps.
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
]

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
		alias: {
			// https://github.com/vitejs/vite/discussions/16730#discussioncomment-13048825
			vue: 'vue/dist/vue.esm-bundler.js',
			'tailwind.config.js': path.resolve(__dirname, 'tailwind.config.js'),
		},
		// A linked frappe-ui brings its own copy of these, and echarts keeps its
		// renderers, series and registered geographies in module state — so a
		// second instance means `registerMap` here and `init` in there disagree
		// about which maps exist. No-op while frappe-ui comes from the registry.
		dedupe: ['echarts', 'zrender', 'vue', '@vueuse/core'],
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
			// echarts keeps its module registry in `echarts/core`, and every
			// subpath writes into it. frappe-ui is excluded below, so a subpath
			// only it imports would be served raw and pull in a second core —
			// one that registers the grid a chart then cannot find. Naming all
			// five puts them in a single optimize run, behind one core.
			...echartsEntries,
			...tiptapDeps,
		],
		exclude: ['frappe-ui'],
	},
	define: {
		// enable hydration mismatch details in production build
		__VUE_PROD_HYDRATION_MISMATCH_DETAILS__: 'true',
	},
})
