import { call } from 'frappe-ui'
import { computed, reactive, ref, watchEffect } from 'vue'
import { createToast } from './toasts'

type DocumentResourceOptions<T> = {
	initialDoc: T
	transform?: (doc: T) => T
}
export default function useDocumentResource<T>(
	doctype: string,
	name: string,
	options: DocumentResourceOptions<T>
) {
	const tranformFn = options.transform || ((doc: T) => doc)
	const beforeInsertFns = new Set<Function>()
	const afterInsertFns = new Set<Function>()
	const beforeSaveFns = new Set<Function>()
	const afterSaveFns = new Set<Function>()

	const resource = reactive({
		doctype,
		doc: options.initialDoc,
		originalDoc: options.initialDoc,
		isdirty: computed(() => false),
		islocal: name.startsWith('new-'),
		loading: !name.startsWith('new-'),
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
			})
			this.doc = tranformFn({ ...doc })
			this.originalDoc = JSON.parse(JSON.stringify(this.doc))
			this.islocal = false
			await Promise.all(Array.from(afterInsertFns).map((fn) => fn()))
			return doc
		},
		onAfterInsert: (fn: Function) => afterInsertFns.add(fn),

		onBeforeSave: (fn: Function) => beforeSaveFns.add(fn),
		async save() {
			if (this.saving) {
				console.log('Already saving', doctype, name)
				return
			}
			if (!this.isdirty && !this.islocal) {
				createToast({
					title: 'No changes to save',
					variant: 'info',
				})
				return
			}

			this.saving = true
			await Promise.all(Array.from(beforeSaveFns).map((fn) => fn()))

			if (this.islocal) {
				await this.insert()
			} else {
				const doc = await call('frappe.client.set_value', {
					doctype,
					name,
					fieldname: removeMetaFields(this.doc),
				})
				this.doc = tranformFn({ ...doc })
				this.originalDoc = JSON.parse(JSON.stringify(this.doc))
			}

			this.islocal = false
			this.saving = false
			await Promise.all(Array.from(afterSaveFns).map((fn) => fn()))
			return this.doc
		},
		onAfterSave: (fn: Function) => afterSaveFns.add(fn),

		async load() {
			if (this.islocal) return
			this.loading = true
			const doc = await call('frappe.client.get', { doctype, name })
			this.doc = tranformFn({ ...doc })
			this.originalDoc = JSON.parse(JSON.stringify(this.doc))
			this.loading = false
		},

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
			this.loading = false
			return response.message
		},

		async delete() {
			this.deleting = true
			await call('frappe.client.delete', { doctype, name })
			this.deleting = false
		},
	})

	resource.load()
	// @ts-ignore
	resource.isdirty = computed(
		() => JSON.stringify(resource.doc) !== JSON.stringify(resource.originalDoc)
	)

	return resource
}

export type DocumentResource<T> = ReturnType<typeof useDocumentResource<T>>

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
