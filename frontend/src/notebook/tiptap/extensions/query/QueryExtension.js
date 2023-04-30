import { mergeAttributes, Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'

import QueryWrapper from './QueryWrapper.vue'

export default Node.create({
	name: 'query',
	group: 'block',
	atom: true,

	addAttributes() {
		return {
			query: undefined,
		}
	},

	parseHTML() {
		return [
			{
				tag: 'query-wrapper',
			},
		]
	},

	renderHTML({ HTMLAttributes }) {
		return ['query-wrapper', mergeAttributes(HTMLAttributes)]
	},

	addNodeView() {
		return VueNodeViewRenderer(QueryWrapper)
	},
})
