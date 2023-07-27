import { createNodeExtension } from './utils'

import Query from './Query.vue'
export default createNodeExtension({
	name: 'query-editor',
	tag: 'query-editor',
	component: Query,
	attributes: {
		query: undefined,
	},
})
