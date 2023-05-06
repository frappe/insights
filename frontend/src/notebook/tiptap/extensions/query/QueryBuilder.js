import { createNodeExtension } from '../utils'

import QueryBuilder from './QueryBuilder.vue'
export default createNodeExtension({
	name: 'query',
	tag: 'query',
	component: QueryBuilder,
	attributes: {
		name: undefined,
		is_native: undefined,
	},
})
