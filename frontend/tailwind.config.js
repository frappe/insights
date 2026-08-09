import containerQueries from '@tailwindcss/container-queries'
import frappeUIPreset, { content as frappeUIContent } from 'frappe-ui/tailwind'

export default {
	presets: [frappeUIPreset],
	content: [
		'./index.html',
		'./src2/**/*.{vue,js,ts,jsx,tsx}',
		// frappe-ui says which of its own files emit classes. A hand-kept list
		// here rots every time a family moves, and it rots silently: a class that
		// is never scanned is not an error, it is a component that quietly draws
		// wrong. Two have already been lost that way — the chart card's corner,
		// and the list's grid.
		...frappeUIContent,
		// ListView is parked in `frappe-ui/experimental`, which that list leaves
		// out on purpose: experimental carries no stability promise, so it is not
		// part of the content contract. Insights depends on it anyway — the root
		// export is gone and this is the only ListView there is — so it scans it
		// itself. Remove this when the list moves to `frappe-ui/list`.
		'./node_modules/frappe-ui/experimental/ListView/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/experimental/ListView/**/*.{vue,js,ts,jsx,tsx}',
	],
	theme: {
		container: {
			center: true,
			padding: {
				DEFAULT: '1rem',
				sm: '2rem',
				lg: '2rem',
				xl: '4rem',
				'2xl': '4rem',
			},
		},
		extend: {
			maxWidth: {
				'main-content': '768px',
			},
			screens: {
				standalone: {
					raw: '(display-mode: standalone)',
				},
			},
		},
	},
	plugins: [containerQueries],
}
