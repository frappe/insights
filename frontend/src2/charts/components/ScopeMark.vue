<script setup lang="ts">
import { Lock } from 'lucide-vue-next'
import { computed } from 'vue'
import { scopeText, type AppliedUserPermission } from '../scoped_by'
import TitleMark from './TitleMark.vue'

// Tells the reader that their own permissions narrowed these cells.
const props = defineProps<{ applied?: AppliedUserPermission[]; narrowed?: boolean }>()

const scope = computed(() => scopeText(props.applied, props.narrowed))
</script>

<template>
	<!-- each doctype on its own line -->
	<TitleMark v-if="scope" :icon="Lock" :label="scope.sentence">
		<div>{{ scope.heading }}</div>
		<div v-for="line in scope.lines" :key="line">{{ line }}</div>
	</TitleMark>
</template>
