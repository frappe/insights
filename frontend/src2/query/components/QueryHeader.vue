<script setup lang="ts">
import { inject } from 'vue'
import ContentEditable from '../../components/ContentEditable.vue'
import { __ } from '../../translation'
import { Query } from '../query'

// The page's header: what the query is, and the acts that change it. Execute,
// the query menu and the data source act on the query, so they cannot sit in
// the result pane below — a code editor stands between the two.
const query = inject('query') as Query
</script>

<template>
	<div class="flex h-7 w-full flex-shrink-0 items-center justify-between gap-3">
		<ContentEditable
			class="-ml-2 w-fit max-w-full text-md-medium !text-ink-gray-7"
			:model-value="query.doc.title"
			:placeholder="__('Untitled Query')"
			@returned="query.doc.title = $event"
			@blur="query.doc.title = $event"
		></ContentEditable>

		<div class="flex flex-shrink-0 items-center gap-2">
			<slot />
		</div>
	</div>
</template>
