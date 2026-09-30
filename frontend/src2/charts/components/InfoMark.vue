<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { InfoIcon } from 'lucide-vue-next'

// A chart's info, behind a mark beside its title. Sized in `em`, like
// `ScopeMark`, so it matches the title it sits beside.
const props = defineProps<{ text: string }>()
</script>

<template>
	<Tooltip>
		<!-- A tooltip grows to its content and never wraps, so this body sets the
		     width and keeps the author's line breaks. -->
		<template #content>
			<div class="max-w-xs whitespace-pre-line">{{ props.text }}</div>
		</template>
		<span class="flex items-center" role="img" :aria-label="props.text" tabindex="0">
			<InfoIcon class="size-[0.85em] text-ink-gray-5" stroke-width="1.5" />
		</span>
	</Tooltip>
</template>
