import { createNodeExtension } from './utils'

import Query from './Query.vue'
export default createNodeExtension({
	name: 'query-builder',
	tag: 'query-builder',
	component: Query,
	attributes: {
		query: undefined,
	},
})
