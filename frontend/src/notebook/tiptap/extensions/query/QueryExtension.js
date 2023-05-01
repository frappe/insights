import { mergeAttributes, Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'

import QueryWrapper from './QueryWrapper.vue'

export default Node.create({
	name: 'query',
	group: 'block',
	atom: true,

	addAttributes() {
		return {
			name: undefined,
		}
	},

	parseHTML() {
		return [
			{
				tag: 'query',
			},
		]
	},

	renderHTML({ HTMLAttributes }) {
		return ['query', mergeAttributes(HTMLAttributes)]
	},

	addNodeView() {
		return VueNodeViewRenderer(QueryWrapper)
	},
})
