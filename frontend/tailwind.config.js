import containerQueries from '@tailwindcss/container-queries'
import frappeUIPreset from 'frappe-ui/tailwind'

export default {
	presets: [frappeUIPreset],
	content: [
		'./index.html',
		'./src2/**/*.{vue,js,ts,jsx,tsx}',
		// charts v2 lives beside `components`, not under it. Leaving it out drops
		// every class only its cards use — `rounded-7`, `bg-surface-elevation-2` —
		// so the card draws square and flat instead of rounded and raised.
		'./node_modules/frappe-ui/src/{components,charts}/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/src/{components,charts}/**/*.{vue,js,ts,jsx,tsx}',
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
