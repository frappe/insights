<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import type { Component } from 'vue'

// A mark beside a chart's title: optional information, shown on hover or focus.
// Sized in `em`, so it matches the title it sits beside, whichever that is: a
// card, a table or a drill level.
const props = defineProps<{ icon: Component; label: string }>()
</script>

<template>
	<Tooltip>
		<!-- A tooltip grows to its content and never wraps, so this body sets the
		     width. -->
		<template #content>
			<div class="max-w-xs whitespace-normal">
				<slot />
			</div>
		</template>
		<span class="flex items-center" role="img" :aria-label="props.label" tabindex="0">
			<component :is="props.icon" class="size-[0.85em] text-ink-gray-5" stroke-width="1.5" />
		</span>
	</Tooltip>
</template>
