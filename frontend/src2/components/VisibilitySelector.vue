<script setup lang="ts">
import { computed } from 'vue'
import { __ } from '../translation'
import { Visibility } from '../types/workbook.types'
import useRoleStore from '../users/roles'

const visibility = defineModel<Visibility>('visibility', { required: true })
const roles = defineModel<string[]>('roles', { required: true })

const roleStore = useRoleStore()

const rungs = computed(() => [
	{
		label: __('Only me and people I share with'),
		value: 'Private',
	},
	{
		label: __('Anyone with a selected role'),
		value: 'Specific Roles',
	},
	{
		label: __('Anyone signed in to this site'),
		value: 'Everyone',
	},
	{
		label: __('Anyone with the link, including guests'),
		value: 'Public',
	},
])

const roleOptions = computed(() => roleStore.roles.map((role) => ({ label: role, value: role })))
</script>

<template>
	<div class="flex flex-col gap-2">
		<span class="text-sm text-ink-gray-5">{{ __('Who can view') }}</span>
		<div class="flex gap-2">
			<div class="flex-1">
				<Combobox
					v-model="visibility"
					:options="rungs"
					:placeholder="__('Select an option')"
				/>
			</div>
			<slot name="actions" />
		</div>
		<MultiSelect
			v-if="visibility === 'Specific Roles'"
			v-model="roles"
			class="w-full"
			:options="roleOptions"
			:loading="roleStore.loading"
			:placeholder="__('Select roles')"
		>
			<template #summary>
				<span class="text-ink-gray-4">{{ __('Select roles') }}</span>
			</template>
		</MultiSelect>
	</div>
</template>
