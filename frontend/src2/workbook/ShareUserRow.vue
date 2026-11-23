<script setup lang="ts">
import { Avatar, Button, Dropdown } from 'frappe-ui'
import { __ } from '../translation'

// One person in a share list: who they are, and what they may do. The share
// dialogs list people with it, and the upgrade wizard pictures them with it.
//
// The default slot replaces the access control, for a list whose rows end in
// something else, such as a team member's remove button.
const props = defineProps<{
	fullName: string
	email: string
	image?: string
	/** `owner` shows a disabled Owner button in place of the access menu. */
	access?: 'edit' | 'view' | 'owner'
	options?: { label: string; value?: string; onClick?: () => void }[]
}>()
</script>

<template>
	<div class="flex w-full items-center gap-2 py-1">
		<Avatar size="xl" :label="props.fullName" :image="props.image" />
		<div class="flex min-w-0 flex-1 flex-col">
			<div class="truncate leading-5">{{ props.fullName }}</div>
			<div class="truncate text-xs text-ink-gray-5">{{ props.email }}</div>
		</div>
		<slot>
			<Button
				v-if="props.access === 'owner'"
				variant="ghost"
				:label="__('Owner')"
				disabled
				class="flex-shrink-0"
			/>
			<Dropdown
				v-else-if="props.access"
				class="flex-shrink-0"
				align="end"
				:options="props.options ?? []"
				:button="{
					iconRight: 'lucide-chevron-down',
					variant: 'ghost',
					label: props.access === 'edit' ? __('Can Edit') : __('Can View'),
				}"
			/>
		</slot>
	</div>
</template>
