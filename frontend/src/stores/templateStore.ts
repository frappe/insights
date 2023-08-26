import { getAllTemplatesResource, getCreateTemplateResource, getMyTemplatesResource } from '@/api'
import { safeJSONParse } from '@/utils'
import dayjs from '@/utils/dayjs'
import { defineStore } from 'pinia'
import { computed } from 'vue'

interface Template {
	name: string
	title: string
	description: string
	author: string
	author_name: string
	status: string
	modified: string
	modifiedFromNow: string
	data_sources: Array<{ name: string; type: string }>
	charts: Array<{ title: string; type: string }>
}

interface NewTemplate {
	title: string
	description: string
	dashboard_name: string
}

const useTemplateStore = defineStore('insights:templates', () => {
	const myTemplatesResource: Resource = getMyTemplatesResource()
	const myTemplates = computed<Template[]>(() => {
		if (!myTemplatesResource.data) return []
		return myTemplatesResource.data?.map(toTemplate)
	})

	const createTemplateResource: Resource = getCreateTemplateResource()
	async function createTemplate(template: NewTemplate) {
		await createTemplateResource.submit({
			template: {
				title: template.title,
				description: template.description,
				dashboard_name: template.dashboard_name,
			},
		})
		myTemplatesResource.reload()
	}

	const allTemplatesResource: Resource = getAllTemplatesResource()
	const allTemplates = computed<Template[]>(() => {
		if (!allTemplatesResource.data) return []
		return allTemplatesResource.data?.map(toTemplate)
	})

	return {
		myTemplates,
		allTemplates,
		creating: createTemplateResource.loading,
		loading: computed(() => myTemplatesResource.loading || allTemplatesResource.loading),
		createTemplate,
	}
})

export default useTemplateStore

function toTemplate(template: any): Template {
	const metadata = safeJSONParse(template.metadata)
	return {
		name: template.name,
		title: template.title,
		description: template.description,
		author: template.author,
		author_name: template.author_name,
		status: template.status,
		modified: template.modified,
		modifiedFromNow: dayjs(template.modified).fromNow(),
		charts: metadata?.charts.map((c: any) => ({ title: c.title, type: c.chart_type })) ?? [],
		data_sources: metadata?.data_sources.map((ds: any) => ({ name: ds.name, type: ds.database_type })) ?? [],
	}
}
