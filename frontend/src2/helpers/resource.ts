import { useStorage, watchDebounced } from '@vueuse/core'
import { call } from 'frappe-ui'
import { computed, reactive, watchEffect } from 'vue'
import { confirmDialog } from '../helpers/confirm_dialog'
import { copy, showErrorToast, waitUntil } from './index'
import { createToast } from './toasts'

type DocumentResourceOptions<T> = {
	initialDoc: T
	transform?: (doc: T) => T
}
export default function useDocumentResource<T extends object>(
	doctype: string,
	name: string,
	options: DocumentResourceOptions<T>
) {
	const tranformFn = options.transform || ((doc: T) => doc)
	const afterLoadFns = new Set<Function>()
	const beforeInsertFns = new Set<Function>()
	const afterInsertFns = new Set<Function>()
	const beforeSaveFns = new Set<Function>()
	const afterSaveFns = new Set<Function>()

	const resource = reactive({
		doctype,
		name,
		doc: options.initialDoc,
		originalDoc: copy(options.initialDoc),
		isdirty: computed(() => false),
		islocal: name && name.startsWith('new-'),
		loading: name && !name.startsWith('new-'),
		saving: false,
		deleting: false,

		onBeforeInsert: (fn: Function) => beforeInsertFns.add(fn),
		async insert() {
			if (!this.islocal) return
			await Promise.all(Array.from(beforeInsertFns).map((fn) => fn()))
			const doc = await call('frappe.client.insert', {
				doc: {
					doctype,
					...removeMetaFields(this.doc),
				},
			}).catch(showErrorToast)
			this.doc = tranformFn({ ...doc })
			this.originalDoc = copy(this.doc)
			this.name = doc.name
			this.islocal = false
			await Promise.all(Array.from(afterInsertFns).map((fn) => fn()))
			return doc
		},
		onAfterInsert: (fn: Function) => afterInsertFns.add(fn),

		onBeforeSave: (fn: Function) => beforeSaveFns.add(fn),
		async save() {
			if (this.saving) {
				console.log('Already saving', this.doctype, this.name)
				await waitUntil(() => !this.saving)
				return this.doc
			}
			if (!this.isdirty && !this.islocal) {
				createToast({
					title: 'No changes to save',
					variant: 'info',
				})
				return this.doc
			}

			this.saving = true
			await Promise.all(Array.from(beforeSaveFns).map((fn) => fn()))

			if (this.islocal) {
				await this.insert()
			} else {
				const doc = await call('frappe.client.set_value', {
					doctype: this.doctype,
					name: this.name,
					fieldname: removeMetaFields(this.doc),
				}).catch(showErrorToast)

				if (doc) {
					this.doc = tranformFn({ ...doc })
					this.originalDoc = copy(this.doc)
				}
			}

			this.saving = false
			await Promise.all(Array.from(afterSaveFns).map((fn) => fn()))
			return this.doc
		},
		onAfterSave: (fn: Function) => afterSaveFns.add(fn),

		discard() {
			confirmDialog({
				title: 'Discard Changes',
				message: 'Are you sure you want to discard changes?',
				onSuccess: () => this.load(),
			})
		},

		async load() {
			if (this.islocal) return
			this.loading = true
			const doc = await call('frappe.client.get', {
				doctype: this.doctype,
				name: this.name,
			}).catch(showErrorToast)

			if (!doc) return

			this.doc = tranformFn({ ...doc })
			this.originalDoc = copy(this.doc)
			await Promise.all(Array.from(afterLoadFns).map((fn) => fn(this.doc)))
			this.loading = false
		},
		onAfterLoad: (fn: Function) => afterLoadFns.add(fn),

		async call(method: string, args = {}) {
			this.loading = true
			const response = await call('run_doc_method', {
				method,
				docs: {
					...this.doc,
					__islocal: this.islocal,
				},
				args,
			})
				.catch(showErrorToast)
				.finally(() => (this.loading = false))
			return response.message
		},

		async delete() {
			this.deleting = true
			await call('frappe.client.delete', {
				doctype: this.doctype,
				name: this.name,
			})
				.catch(showErrorToast)
				.finally(() => (this.deleting = false))
		},
	})

	// @ts-ignore
	resource.isdirty = computed(
		() => JSON.stringify(resource.doc) !== JSON.stringify(resource.originalDoc)
	)

	resource.load().then(setupLocalStorage)

	function setupLocalStorage() {
		const storageKey = `insights:resource:${resource.doctype}:${resource.name}`
		const storage = useStorage(storageKey, {
			doc: null as any,
			originalDoc: null as any,
		})
		// on creation, restore the doc from local storage, if exists
		if (storage.value && storage.value.doc) {
			resource.doc = storage.value.doc
			resource.originalDoc = storage.value.originalDoc
		}
		// watch for changes in doc and save it to local storage
		watchDebounced(
			() => resource.isdirty,
			() => {
				storage.value = resource.isdirty
					? {
							doc: resource.doc,
							originalDoc: resource.originalDoc,
					  }
					: null
			},
			{ debounce: 500, immediate: true }
		)
	}

	return resource
}

export type DocumentResource<T extends object> = ReturnType<typeof useDocumentResource<T>>

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
