<script setup lang="ts">
import { MoreHorizontal } from 'lucide-vue-next'
import { computed } from 'vue'
import { APP_PATH } from '../app_path'
import type { DashboardAction } from './view'

// The first action renders as a button, and the rest go in one menu.
// `DashboardBody` decides which actions there are.
const props = defineProps<{ actions: DashboardAction[] }>()

const first = computed(() => props.actions[0])
const rest = computed(() => props.actions.slice(1).map(toOption))

// An action holds the bare lucide name, because a host outside Insights uses
// its own icon component. frappe-ui names the same icon `lucide-<name>`.
function iconClass(action: DashboardAction) {
	return action.icon ? `lucide-${action.icon}` : undefined
}

// `resolveHref` returns a URL under the app's base, but the router matches the
// path without it. So the same constant removes it here.
function toRoute(href: string) {
	return href.startsWith(APP_PATH) ? href.slice(APP_PATH.length) || '/' : href
}

// A `route` renders as a router link on both a Button and a menu item, so the
// link stays in the app.
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
