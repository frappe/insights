import { useStorage, watchDebounced } from '@vueuse/core'
import { isEqual } from 'es-toolkit'
import { call } from 'frappe-ui'
import { onDocUpdate } from 'frappe-ui/src/resources/realtime'
import { computed, reactive, ref, UnwrapRef } from 'vue'
import { confirmDialog } from '../helpers/confirm_dialog'
import { getSocket } from '../socket'
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

	const isDirty = computed(() => !isEqual(doc.value, originalDoc.value))

	async function insertDoc() {
		if (!isLocal.value) return
		await executeHooks(lifecycleHooks.beforeInsert)

		isSaving.value = true
		const newDoc = await call(methods.insert, {
			doc: {
				doctype,
				...removeMetaFields(doc.value),
			},
		})
			.catch(showErrorToast)
			.finally(() => (isSaving.value = false))

		updateDocState(newDoc)
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
		const newDoc = await call(methods.update, {
			doctype,
			name: docname.value,
			fieldname: removeMetaFields(doc.value),
		})
			.catch(showErrorToast)
			.finally(() => (isSaving.value = false))

		if (newDoc) {
			updateDocState(newDoc)
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

	function updateDocState(newDoc: any) {
		doc.value = transformFn({ ...newDoc }) as UnwrapRef<T>
		originalDoc.value = copy(doc.value)
		docname.value = newDoc.name
	}

	const executeHooks = async (hooks: Set<Function>, args: any[] = []) => {
		await Promise.all(Array.from(hooks).map((fn) => fn(...args)))
	}

	const setupAutoSave = () => {
		watchToggle(isDirty, saveDoc, {
			toggleCondition: () => autoSave.value && !isLocal.value,
			immediate: true,
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
		const socket = getSocket()
		onDocUpdate(socket, doctype, (name: string) => {
			if (String(name) === String(docname.value)) {
				loadDoc()
			}
		})
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
				title: 'Discard Changes',
				message: 'Are you sure you want to discard changes?',
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
