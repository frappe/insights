import { useStorage, watchDebounced } from '@vueuse/core'
import { __ } from '../translation'
import { isEqual } from 'es-toolkit'
import { call } from 'frappe-ui'
import { computed, reactive, ref, UnwrapRef } from 'vue'
import { confirmDialog } from '../helpers/confirm_dialog'
import { copy, showErrorToast, waitUntil, watchToggle } from './index'
// import json_diff from 'https://cdn.jsdelivr.net/npm/json-diff@1.0.6/+esm'

type Document = {
	doctype: string
	name: string
	owner: string
	[key: string]: any
}

const DEFAULT_API = {
	get: 'insights.api.get_doc',
	insert: 'frappe.client.insert',
	update: 'frappe.client.set_value',
	delete: 'frappe.client.delete',
	call: 'insights.api.run_doc_method',
}

type ApiMethods = typeof DEFAULT_API

type DocumentResourceOptions<T extends Document> = {
	initialDoc: T
	transform?: (doc: T) => T
	enableAutoSave?: boolean
	disableLocalStorage?: boolean
	apiMethods?: Partial<ApiMethods>
}

export default function useDocumentResource<T extends Document>(
	doctype: string,
	name: string,
	options: DocumentResourceOptions<T>
) {
	const doc = ref(options.initialDoc)
	const originalDoc = ref(copy(options.initialDoc))
	const docname = ref(String(name))
	const isLocal = ref(docname.value.startsWith('new-'))
	const isLoading = ref(docname.value && !docname.value.startsWith('new-'))
	const isLoaded = ref(false)
	const isSaving = ref(false)
	const isDeleting = ref(false)
	const autoSave = ref(options.enableAutoSave ?? false)

	const methods = { ...DEFAULT_API, ...options.apiMethods }

	const lifecycleHooks = {
		afterLoad: new Set<Function>(),
		beforeInsert: new Set<Function>(),
		afterInsert: new Set<Function>(),
		beforeSave: new Set<Function>(),
		afterSave: new Set<Function>(),
	}

	const transformFn = options.transform || ((doc: T) => doc)

	// Both sides go through `copy` because `originalDoc` is one: a key set to
	// `undefined` is dropped by the clone and kept on the document, and a deep
	// equality that counts keys then calls a document dirty that a save cannot
	// clean — autoSave writes it, the response replaces the document, whatever
	// wrote the `undefined` writes it again.
	const isDirty = computed(() => !isEqual(copy(doc.value), originalDoc.value))

	async function insertDoc() {
		if (!isLocal.value) return
		await executeHooks(lifecycleHooks.beforeInsert)

		isSaving.value = true
		const sentDoc = copy(removeMetaFields(doc.value))
		const newDoc = await call(methods.insert, {
			doc: {
				doctype,
				...sentDoc,
			},
		})
			.catch(showErrorToast)
			.finally(() => (isSaving.value = false))

		updateDocState(newDoc, sentDoc)
		isLocal.value = false
		await executeHooks(lifecycleHooks.afterInsert)
		return newDoc
	}

	async function saveDoc() {
		if (isSaving.value) {
			await waitUntil(() => !isSaving.value)
			return doc.value
		}

		if (!isDirty.value && !isLocal.value) {
			return doc.value
		}

		isSaving.value = true
		await executeHooks(lifecycleHooks.beforeSave)

		if (isLocal.value) {
			await insertDoc()
		} else {
			await updateDoc()
		}

		isSaving.value = false
		await executeHooks(lifecycleHooks.afterSave)

		return doc.value
	}

	async function updateDoc() {
		isSaving.value = true
		const sentDoc = copy(removeMetaFields(doc.value))
		const newDoc = await call(methods.update, {
			doctype,
			name: docname.value,
			fieldname: sentDoc,
		})
			.catch(showErrorToast)
			.finally(() => (isSaving.value = false))

		if (newDoc) {
			updateDocState(newDoc, sentDoc)
		}
	}

	async function loadDoc() {
		if (isLocal.value) return

		isLoading.value = true

		const _doc = await call(methods.get, {
			doctype,
			name: docname.value,
		})
			.catch(showErrorToast)
			.finally(() => (isLoading.value = false))

		if (!_doc) return

		updateDocState(_doc)
		await executeHooks(lifecycleHooks.afterLoad, [doc.value])
		isLoading.value = false
		isLoaded.value = true
	}

	async function callMethod(method: string, args: any = {}) {
		isLoading.value = true
		const response = await call(methods.call, {
			method,
			docs: {
				...(doc.value || {}),
				__islocal: isLocal.value,
			},
			args,
		})
			.catch(showErrorToast)
			.finally(() => (isLoading.value = false))
		return response.message
	}

	async function deleteDoc() {
		isDeleting.value = true
		await call(methods.delete, {
			doctype: doctype,
			name: docname.value,
		})
			.catch(showErrorToast)
			.finally(() => (isDeleting.value = false))
	}

	// `sentDoc` is the deep clone a write carried. Pass it to keep the edits the
	// user made while that write was in flight. Leave it out to replace the
	// document, which is what a load wants.
	function updateDocState(newDoc: any, sentDoc?: any) {
		const currentDoc = removeMetaFields(doc.value)
		const answer = transformFn({ ...newDoc }) as UnwrapRef<T>

		// The answer says what the server holds, so it is the new baseline even
		// where the document has moved past it.
		originalDoc.value = copy(answer)

		if (sentDoc) {
			for (const field of Object.keys(currentDoc)) {
				const current = copy(currentDoc[field])
				// An `undefined` value is dropped by `copy`, so keeping one here
				// would make the document dirty forever. Let the answer win.
				if (current === undefined) continue
				if (isEqual(current, sentDoc[field])) continue
				// The field moved after the write left, so the newer value wins.
				;(answer as any)[field] = current
			}
		}

		doc.value = answer
		docname.value = newDoc.name
	}

	const executeHooks = async (hooks: Set<Function>, args: any[] = []) => {
		await Promise.all(Array.from(hooks).map((fn) => fn(...args)))
	}

	const setupAutoSave = () => {
		// Watch the document, not `isDirty`. `isDirty` is a boolean, so an edit
		// that lands while a write is in flight leaves it true and raises no
		// new edge. The document itself changes, so the debounce re-arms and
		// the kept edit reaches the server.
		watchToggle(doc, () => isDirty.value && saveDoc(), {
			toggleCondition: () => autoSave.value && !isLocal.value,
			immediate: true,
			deep: true,
			debounce: 1500,
		})
	}

	const setupLocalStorage = () => {
		if (options.disableLocalStorage) return

		const storageKey = `insights:resource:${doctype}:${docname.value}`
		const storage = useStorage(storageKey, {
			doc: null as any,
			originalDoc: null as any,
		})

		if (storage.value?.doc) {
			const isStale =
				new Date(doc.value.modified).getTime() > new Date(storage.value.doc.modified).getTime()

			if (!isStale) {
				doc.value = storage.value.doc
				originalDoc.value = storage.value.originalDoc
			}
		}

		watchDebounced(
			isDirty,
			() => {
				storage.value = isDirty.value
					? {
							doc: doc.value,
							originalDoc: originalDoc.value,
					  }
					: null
			},
			{
				immediate: true,
				deep: true,
			}
		)
	}

	const setupRealtimeUpdates = () => {
		// const socket = getSocket()
		// onDocUpdate(socket, doctype, (name: string) => {
		// 	if (String(name) === String(docname.value)) {
		// 		loadDoc()
		// 	}
		// })
	}

	loadDoc().then(setupLocalStorage).then(setupAutoSave)
	// setupRealtimeUpdates()

	return reactive({
		doctype,
		name: docname,
		doc: doc,
		originalDoc: originalDoc,
		isdirty: isDirty,
		islocal: isLocal,
		loading: isLoading,
		isloaded: isLoaded,
		saving: isSaving,
		deleting: isDeleting,
		autoSave: autoSave,

		onBeforeInsert: (fn: Function) => lifecycleHooks.beforeInsert.add(fn),
		onAfterInsert: (fn: Function) => lifecycleHooks.afterInsert.add(fn),
		onBeforeSave: (fn: Function) => lifecycleHooks.beforeSave.add(fn),
		onAfterSave: (fn: Function) => lifecycleHooks.afterSave.add(fn),
		onAfterLoad: (fn: Function) => lifecycleHooks.afterLoad.add(fn),

		insert: insertDoc,
		save: saveDoc,
		load: loadDoc,
		call: callMethod,
		delete: deleteDoc,

		discard() {
			confirmDialog({
				title: __('Discard Changes'),
				message: __('Are you sure you want to discard changes?'),
				onSuccess: () => loadDoc(),
			})
		},
	})
}

export type DocumentResource<T extends Document> = ReturnType<typeof useDocumentResource<T>>

const metaFields = [
	'doctype',
	'name',
	'owner',
	'creation',
	'modified',
	'modified_by',
	'docstatus',
	'parent',
	'parentfield',
	'parenttype',
]

function removeMetaFields(doc: any) {
	const newDoc = { ...doc }
	metaFields.forEach((field) => delete newDoc[field])
	return newDoc
}
