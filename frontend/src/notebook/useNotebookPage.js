import { safeJSONParse, useAutoSave } from '@/utils'
import { createDocumentResource } from 'frappe-ui'
import { computed, reactive } from 'vue'

export default function useNotebookPage(page_name) {
	const resource = createDocumentResource({
		doctype: 'Insights Notebook Page',
		name: page_name,
		transform(data) {
			data.content = safeJSONParse(data.content)
			return data
		},
	})
	const state = reactive({
		doc: {},
		loading: false,
	})

	state.reload = async () => {
		state.loading = true
		state.doc = await resource.get.fetch()
		if (isEmpty(state.doc.content)) {
			state.doc.content = getPlaceholderContent()
		}
		state.loading = false
	}
	state.reload()

	state.save = async () => {
		state.loading = true
		state.doc.content = appendLastParagraph(state.doc.content)
		const contentString = JSON.stringify(state.doc.content, null, 2)
		await resource.setValue.submit({
			title: state.doc.title || 'Untitled',
			content: contentString,
		})
		state.loading = false
	}

	const fieldsToWatch = computed(() => {
		// if doc is not loaded, don't watch
		if (!state.doc.name) return
		return {
			title: state.doc.title,
			content: state.doc.content,
		}
	})
	useAutoSave(fieldsToWatch, {
		saveFn: state.save,
		interval: 1500,
	})

	state.delete = async () => {
		state.loading = true
		await resource.delete.submit()
		state.loading = false
	}

	state.addQuery = async (queryType, queryName) => {
		const validTypes = ['query-editor']
		if (!validTypes.includes(queryType)) {
			throw new Error(`Invalid query type: ${queryType}`)
		}
		state.loading = true
		const content = safeJSONParse(state.doc.content)
		content.content.push({
			type: queryType,
			attrs: { query: queryName },
		})
		state.doc.content = content
		await state.save()
		await state.reload()
		state.loading = false
	}

	return state
}

function appendLastParagraph(content) {
	if (typeof content == 'string') content = safeJSONParse(content)
	if (!content.content?.length) return {}
	const lastBlock = content.content?.at(-1)
	if (lastBlock?.type != 'paragraph') {
		content.content.push({
			type: 'paragraph',
			attrs: { textAlign: 'left' },
		})
	}
	return content
}

function isEmpty(content) {
	if (!content) return true
	if (typeof content == 'string') content = safeJSONParse(content)
	if (!content.type) return true
	if (!content.content?.length) return true
}

function getPlaceholderContent() {
	return {
		type: 'doc',
		content: [
			{
				type: 'paragraph',
				attrs: { textAlign: 'left' },
				content: [
					{ type: 'text', text: '❓Don’t know where to start? Start by defining your..' },
				],
			},
			{
				type: 'paragraph',
				attrs: { textAlign: 'left' },
				content: [
					{ type: 'text', marks: [{ type: 'bold' }], text: '🎯 Objective' },
					{ type: 'text', text: ': ' },
					{
						type: 'text',
						marks: [{ type: 'italic' }],
						text: 'We have to find out why so and so…',
					},
				],
			},
			{
				type: 'paragraph',
				attrs: { textAlign: 'left' },
				content: [{ type: 'text', marks: [{ type: 'bold' }], text: '🔍 Approach:' }],
			},
			{
				type: 'bulletList',
				content: [
					{
						type: 'listItem',
						content: [
							{
								type: 'paragraph',
								attrs: { textAlign: 'left' },
								content: [
									{
										type: 'text',
										marks: [{ type: 'italic' }],
										text: 'We start with this data',
									},
								],
							},
						],
					},
					{
						type: 'listItem',
						content: [
							{
								type: 'paragraph',
								attrs: { textAlign: 'left' },
								content: [
									{
										type: 'text',
										marks: [{ type: 'italic' }],
										text: 'Combine with that data',
									},
								],
							},
						],
					},
				],
			},
			{
				type: 'paragraph',
				attrs: { textAlign: 'left' },
				content: [
					{
						type: 'text',
						text: '❌ Want to start from scratch? Use the clear button inside the 3-dot menu ',
					},
				],
			},
		],
	}
}
