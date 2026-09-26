<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { Lock } from 'lucide-vue-next'
import { computed } from 'vue'
import { scopeText, type AppliedUserPermission } from '../scoped_by'

// Tells the reader that their own permissions narrowed these cells. It sits
// beside the title of what it marks: a card, a table or a drill level. Sized in
// `em`, so it matches that title. It is optional information, so it shows on
// hover or focus.
const props = defineProps<{ applied?: AppliedUserPermission[]; narrowed?: boolean }>()

const scope = computed(() => scopeText(props.applied, props.narrowed))
</script>

<template>
	<Tooltip v-if="scope">
		<!-- A tooltip grows to its content and never wraps, so this body sets the
		     width and puts each doctype on its own line. -->
		<template #content>
			<div class="max-w-xs whitespace-normal">
				<div>{{ scope.heading }}</div>
				<div v-for="line in scope.lines" :key="line">{{ line }}</div>
			</div>
		</template>
		<span class="flex items-center" role="img" :aria-label="scope.sentence" tabindex="0">
			<Lock class="size-[0.85em] text-ink-gray-5" stroke-width="1.5" />
		</span>
	</Tooltip>
</template>
