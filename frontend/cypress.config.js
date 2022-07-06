const { defineConfig } = require('cypress')

module.exports = defineConfig({
	component: {
		devServer: {
			framework: 'vue',
			bundler: 'vite',
		},
		specPattern: 'src/tests/components/**/*.test.js',
		viewportWidth: 1280,
		viewportHeight: 720,
	},

	e2e: {
		baseUrl: 'http://frappe-insights:8000',
		env: {
			adminPassword: 'frappe',
		},
		specPattern: 'src/tests/e2e/**/*.test.js',
		viewportWidth: 1280,
		viewportHeight: 720,
		setupNodeEvents(on, config) {
			require('@cypress/code-coverage/task')(on, config)
			return config
		},
	},
})
