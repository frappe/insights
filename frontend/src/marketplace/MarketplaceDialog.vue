<script setup>
import DialogWithSidebar from '@/components/DialogWithSidebar.vue'
import useMarketplaceStore from '@/stores/marketplaceStore'
import { useMagicKeys, whenever } from '@vueuse/core'
import { Globe, User } from 'lucide-vue-next'
import { markRaw } from 'vue'
import MarketplaceTemplateImportDialog from './MarketplaceTemplateImportDialog.vue'
import MyTemplates from './MyTemplates.vue'
import TemplatesBrowser from './TemplatesBrowser.vue'

const marketplaceStore = useMarketplaceStore()
const keys = useMagicKeys()
const escape = keys['Escape']
whenever(escape, () => {
	if (marketplaceStore.marketplaceDialogOpen && !marketplaceStore.importDialogOpen) {
		marketplaceStore.closeMarketplaceDialog()
	}
})
</script>

<template>
	<DialogWithSidebar
		title="Marketplace"
		v-model:show="marketplaceStore.marketplaceDialogOpen"
		:dismissable="false"
		:tabs="[
			{
				label: 'Browse Templates',
				component: markRaw(TemplatesBrowser),
				icon: Globe,
			},
			{
				label: 'My Templates',
				component: markRaw(MyTemplates),
				icon: User,
			},
		]"
	/>

	<MarketplaceTemplateImportDialog />
</template>
