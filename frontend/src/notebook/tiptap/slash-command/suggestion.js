import { VueRenderer } from '@tiptap/vue-3'
import {
	Heading1,
	Heading2,
	Heading3,
	Table,
	ParkingSquare,
	ChevronRightSquare,
} from 'lucide-vue-next'
import tippy from 'tippy.js'

import CommandsList from './CommandsList.vue'
import { markRaw } from 'vue'

export default {
	items: ({ query }) => {
		return [
			{
				title: 'Paragraph',
				icon: ParkingSquare,
				command: ({ editor, range }) => {
					editor.chain().focus().deleteRange(range).setNode('paragraph').run()
				},
			},
			{
				title: 'Heading 1',
				icon: Heading1,
				command: ({ editor, range }) => {
					editor.chain().focus().deleteRange(range).setNode('heading', { level: 2 }).run()
				},
			},
			{
				title: 'Heading 2',
				icon: Heading2,
				command: ({ editor, range }) => {
					editor.chain().focus().deleteRange(range).setNode('heading', { level: 3 }).run()
				},
			},
			{
				title: 'Heading 3',
				icon: Heading3,
				command: ({ editor, range }) => {
					editor.chain().focus().deleteRange(range).setNode('heading', { level: 4 }).run()
				},
			},
			{
				title: 'Table',
				icon: Table,
				command: ({ editor, range }) => {
					editor
						.chain()
						.focus()
						.deleteRange(range)
						.insertTable({ rows: 3, cols: 3, withHeaderRow: true })
						.run()
				},
			},
			{
				title: 'SQL',
				icon: markRaw(ChevronRightSquare),
				command: ({ editor, range }) => {
					const element = '<query-wrapper></query-wrapper>'
					editor.chain().focus().deleteRange(range).insertContent(element).run()
				},
			},
		]
			.filter((item) => item.title.toLowerCase().includes(query.toLowerCase()))
			.slice(0, 5)
	},

	render: () => {
		let component
		let popup

		return {
			onStart: (props) => {
				component = new VueRenderer(CommandsList, {
					props,
					editor: props.editor,
				})

				if (!props.clientRect) {
					return
				}

				popup = tippy('body', {
					getReferenceClientRect: props.clientRect,
					appendTo: () => document.body,
					content: component.element,
					showOnCreate: true,
					interactive: true,
					trigger: 'manual',
					placement: 'bottom-start',
				})
			},

			onUpdate(props) {
				component.updateProps(props)

				if (!props.clientRect) {
					return
				}

				popup[0].setProps({
					getReferenceClientRect: props.clientRect,
				})
			},

			onKeyDown(props) {
				if (props.event.key === 'Escape') {
					popup[0].hide()

					return true
				}

				return component.ref?.onKeyDown(props)
			},

			onExit() {
				popup[0].destroy()
				component.destroy()
			},
		}
	},
}
