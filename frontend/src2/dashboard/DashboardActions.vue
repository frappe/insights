<script setup lang="ts">
import { MoreHorizontal } from 'lucide-vue-next'
import { computed } from 'vue'
import { APP_PATH } from '../app_path'
import type { DashboardAction } from './view'

// The dashboard's actions, as this app draws them: the first one as a button,
// the rest in the page's one menu. Which actions there are is `DashboardBody`'s
// to say — nothing is added or held back here.
const props = defineProps<{ actions: DashboardAction[] }>()

const first = computed(() => props.actions[0])
const rest = computed(() => props.actions.slice(1).map(toOption))

// An action carries the bare lucide name, because a host outside Insights names
// its own icon component. frappe-ui spells the same icon `lucide-<name>`.
function iconClass(action: DashboardAction) {
	return action.icon ? `lucide-${action.icon}` : undefined
}

// `resolveHref` gave a URL under the app's base; the router matches the path
// without it. Two ends of the same seam, so the same constant undoes it.
function toRoute(href: string) {
	return href.startsWith(APP_PATH) ? href.slice(APP_PATH.length) || '/' : href
}

// An action either leads somewhere or runs something. A `route` is a router
// link on both a Button and a menu item, so the link stays in-app.
function target(action: DashboardAction) {
	return 'href' in action ? { route: toRoute(action.href) } : { onClick: action.onClick }
}

function toOption(action: DashboardAction) {
	return { label: action.label, icon: iconClass(action), ...target(action) }
}
</script>

<template>
	<Button
		v-if="first"
		variant="outline"
		:label="first.label"
		:iconLeft="iconClass(first)"
		v-bind="target(first)"
	/>
	<Dropdown v-if="rest.length" align="end" :options="rest">
		<Button variant="outline">
			<template #icon>
				<MoreHorizontal class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
			</template>
		</Button>
	</Dropdown>
</template>
