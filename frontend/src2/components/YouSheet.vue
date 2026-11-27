<script setup lang="ts">
import { BottomSheet } from 'frappe-ui'
import { TrialBanner } from '@framework/ui/components/TrialBanner/index.ts'
import session from '../session'
import { __ } from '../translation'
import UpgradeCard from '../upgrade/UpgradeCard.vue'
import DemoDataBanner from './DemoDataBanner.vue'
import SecurityUpdateCard from './SecurityUpdateCard.vue'
import SidebarLink from './SidebarLink.vue'
import { isFCSite, useUserMenuOptions } from './user_menu'

type Link = { label: string; icon: any; to?: string; onClick?: () => void }

// What the sidebar holds besides its tabs: the user menu, the places the tab bar
// leaves out, and the banners
const props = defineProps<{ links: Link[] }>()
const open = defineModel<boolean>('open', { default: false })

const userOptions = useUserMenuOptions()

function pick(item: { onClick?: () => void }) {
	open.value = false
	item.onClick?.()
}
</script>

<template>
	<BottomSheet v-model:open="open" :title="session.user.full_name || __('You')">
		<div class="flex flex-col gap-1 px-3 pb-6">
			<SidebarLink
				v-for="link in props.links"
				:key="link.label"
				class="h-10"
				:icon="link.icon"
				:label="link.label"
				:to="link.to"
				@click="pick(link)"
			/>
			<div v-if="props.links.length" class="my-1 border-t" />
			<SidebarLink
				v-for="option in userOptions"
				:key="option.label"
				class="h-10"
				:icon="option.icon"
				:label="option.label"
				@click="pick(option)"
			/>
			<DemoDataBanner class="mt-2 p-2" />
			<UpgradeCard class="mt-2" />
			<SecurityUpdateCard class="mt-2" />
			<TrialBanner v-if="isFCSite" :is-sidebar-collapsed="false" />
		</div>
	</BottomSheet>
</template>
