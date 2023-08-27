import {
	getAllTemplatesResource,
	getCreateTemplateResource,
	getImportTemplateResource,
	getMyTemplatesResource,
} from '@/api'
import { safeJSONParse } from '@/utils'
import dayjs from '@/utils/dayjs'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

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
	charts: Array<{ title: string; type: string; data_source: string }>
}

interface NewTemplate {
	title: string
	description: string
	dashboard_name: string
}

const useMarketplaceStore = defineStore('insights:marketplace', () => {
	const marketplaceDialogOpen = ref(false)
	const openMarketplaceDialog = () => (marketplaceDialogOpen.value = true)
	const closeMarketplaceDialog = () => (marketplaceDialogOpen.value = false)

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

	const importDialogTemplate = ref<Template | null>(null)
	const openImportDialog = (template: Template) => (importDialogTemplate.value = template)
	const closeImportDialog = () => (importDialogTemplate.value = null)
	const importDialogOpen = computed({
		get: () => !!importDialogTemplate.value,
		set: (value) => !value && (importDialogTemplate.value = null),
	})

	const importTemplateResource: Resource = getImportTemplateResource()
	function importTemplate(
		template: Template,
		dashboardTitle: string,
		dataSourceMap: Record<string, string>
	) {
		return importTemplateResource.submit({
			dashboard_title: dashboardTitle,
			template_name: template.name,
			data_source_map: dataSourceMap,
		})
	}

	return {
		marketplaceDialogOpen,
		openMarketplaceDialog,
		closeMarketplaceDialog,
		importDialogOpen,
		importDialogTemplate,
		openImportDialog,
		closeImportDialog,
		myTemplates,
		allTemplates,
		creating: createTemplateResource.loading,
		loading: computed(() => myTemplatesResource.loading || allTemplatesResource.loading),
		createTemplate,
		importTemplate,
	}
})

export default useMarketplaceStore

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
		data_sources:
			metadata?.data_sources.map((ds: any) => ({
				name: ds.name,
				type: ds.database_type,
			})) ?? [],
		charts:
			metadata?.charts.map((c: any) => ({
				title: c.title,
				type: c.chart_type,
				data_source: c.data_source,
			})) ?? [],
	}
}
