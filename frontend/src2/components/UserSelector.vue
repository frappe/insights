<script setup lang="ts">
import { SearchIcon } from 'lucide-vue-next'
import { computed } from 'vue'
import useUserStore from '../users/users'

const props = defineProps<{
	placeholder?: string
	hideUsers?: string[]
}>()
const selectedUserEmail = defineModel<string>()

const userStore = useUserStore()
const filteredUsers = computed(() => {
	return userStore.users
		.filter((user) => user.enabled)
		.filter((user) => !props.hideUsers?.includes(user.email))
		.map((user) => {
			return {
				...user,
				label: user.full_name,
				value: user.email,
				description: user.email,
			}
		})
})
</script>

<template>
	<Combobox
		class="w-full"
		:modelValue="selectedUserEmail"
		@update:modelValue="selectedUserEmail = $event"
		:options="filteredUsers"
		:placeholder="props.placeholder || 'Search user...'"
	>
		<template #prefix>
			<SearchIcon class="h-4 w-4 text-ink-gray-4" stroke-width="1.5" />
		</template>

		<template #item-prefix="{ item }">
			<Avatar size="sm" :label="item.label" :image="item.user_image" />
		</template>
	</Combobox>
</template>
