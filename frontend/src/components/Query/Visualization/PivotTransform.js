import { defineComponent, h } from 'vue'

export default defineComponent({
	name: 'PivotTransform',
	props: {
		tableHtml: {
			type: String,
			required: true,
		},
	},
	setup(props) {
		return () =>
			h(
				'div',
				{
					class: 'flex w-full select-text flex-col text-base',
				},
				[
					h('div', {
						class: 'relative overflow-scroll scrollbar-hide border',
						innerHTML: props.tableHtml,
					}),
				]
			)
	},
})
