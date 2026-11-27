<script setup lang="ts">
import { MobileNav, MobileNavItem } from 'frappe-ui'
import { CircleUser } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { __ } from '../translation'
import { useNavLinks } from './nav_links'
import YouSheet from './YouSheet.vue'

// The phone's way around the app, in place of the sidebar. The places a reader
// may open are tabs. The rest of the sidebar, and the user menu, are in You.
const route = useRoute()
const router = useRouter()
const links = useNavLinks()
const YOU_SHEET_LINKS = ['DataStoreList']
const tabs = computed(() =>
	links.value.filter((link) => link.to && !link.hidden && !YOU_SHEET_LINKS.includes(link.to)),
)

// a tab stays lit on every page under it, such as a dashboard under Dashboards
function isUnder(name: string) {
	return route.path.startsWith(router.resolve({ name }).path)
}

const showYouSheet = ref(false)
</script>

<template>
	<MobileNav class="sm:hidden">
		<MobileNavItem
			v-for="tab in tabs"
			:key="tab.to"
			:label="tab.label"
			:icon="tab.icon"
			:route="{ name: tab.to! }"
			:active="isUnder(tab.to!)"
		/>
		<MobileNavItem
			:label="__('You')"
			:icon="CircleUser"
			:active="showYouSheet"
			@click="showYouSheet = true"
		/>
	</MobileNav>
	<YouSheet
		v-model:open="showYouSheet"
		:links="links.filter((link) => !link.hidden && !tabs.includes(link))"
	/>
</template>
