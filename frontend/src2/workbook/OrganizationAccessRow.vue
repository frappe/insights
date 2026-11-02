<script setup lang="ts">
import { Dropdown } from 'frappe-ui'
import { Building2 } from 'lucide-vue-next'
import { __ } from '../translation'

// Whether everyone signed in to the site may open a workbook, and how. The
// workbook's share dialog sets it here, and the upgrade wizard pictures it.
const props = defineProps<{
	access?: 'view' | 'edit'
	options?: { label: string; onClick?: () => void }[]
}>()
</script>

<template>
	<div class="flex items-center gap-3 rounded-4 border px-3 py-2">
		<Building2 class="h-6 w-6 text-ink-blue-5" stroke-width="1.5" />
		<div class="flex flex-1 flex-col">
			<div class="font-medium leading-5 text-ink-gray-7">{{ __('Organization Access') }}</div>
			<div class="text-sm text-ink-gray-6">
				{{
					props.access === 'edit'
						? __('All users in your organization can edit')
						: props.access === 'view'
						  ? __('All users in your organization can view')
						  : __('Only you have access to this workbook')
				}}
			</div>
		</div>
		<Dropdown
			:options="props.options ?? []"
			:button="{
				iconRight: 'lucide-chevron-down',
				label:
					props.access === 'edit'
						? __('Can Edit')
						: props.access === 'view'
						  ? __('Can View')
						  : __('Disabled'),
			}"
		/>
	</div>
</template>
