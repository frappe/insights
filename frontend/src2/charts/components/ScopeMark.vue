<script setup lang="ts">
import { Tooltip } from 'frappe-ui'
import { Lock } from 'lucide-vue-next'
import { computed } from 'vue'
import { scopeText, type AppliedUserPermission } from '../scoped_by'

// What cells the reader's own permissions narrowed say, beside whatever names
// them: a card's title, a table's, a drill level's. Sized in `em`, so the mark is
// the size of the text it sits on. Optional information, so it waits for a hover
// or a tab stop, and nothing is drawn without a scope.
const props = defineProps<{ applied?: AppliedUserPermission[]; narrowed?: boolean }>()

const scope = computed(() => scopeText(props.applied, props.narrowed))
</script>

<template>
	<Tooltip v-if="scope">
		<!-- A bubble grows to its content and never wraps, so a line per doctype
		     is a width the body sets and lines it draws. -->
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
