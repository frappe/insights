import { mergeAttributes, Node } from '@tiptap/core'
import { VueNodeViewRenderer } from '@tiptap/vue-3'

export function createNodeExtension(options) {
	const { name, component, tag, ...rest } = options
	return Node.create({
		name,
		group: rest.group || 'block',
		atom: rest.atom || true,
		addAttributes() {
			return rest.attributes || {}
		},
		parseHTML() {
			return [{ tag }]
		},
		renderHTML({ HTMLAttributes }) {
			return [tag, mergeAttributes(HTMLAttributes)]
		},
		addNodeView() {
			return VueNodeViewRenderer(component)
		},
	})
}
