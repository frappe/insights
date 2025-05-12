<script setup lang="ts">
import { SearchIcon } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import useUserStore from '../users/users'

const props = defineProps<{
	placeholder?: string
	hideUsers?: string[]
}>()
const selectedUserEmail = defineModel<string>()

const userStore = useUserStore()
const searchTxt = ref('')
watchEffect(() => {
	searchTxt.value = selectedUserEmail.value || ''
})
const filteredUsers = computed(() => {
	return userStore.users
		.filter((user) => {
			if (!user.enabled) return false
			if (!searchTxt.value) return true
			return (
				user.full_name.toLowerCase().includes(searchTxt.value.toLowerCase()) ||
				user.email.toLowerCase().includes(searchTxt.value.toLowerCase())
			)
		})
		.filter((user) => {
			return !props.hideUsers?.includes(user.email)
		})
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
	<Autocomplete
		:hide-search="true"
		:autofocus="false"
		:modelValue="selectedUserEmail"
		@update:modelValue="selectedUserEmail = $event?.value"
		:options="filteredUsers"
	>
		<template #target="{ open }">
			<FormControl
				class="w-full"
				type="text"
				:placeholder="props.placeholder || 'Search user...'"
				autocomplete="off"
				v-model="searchTxt"
				@update:modelValue="open"
				@focus="open"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" stroke-width="1.5" />
				</template>
			</FormControl>
		</template>

		<template #item-prefix="{ option }">
			<Avatar size="sm" :label="option.label" :image="option.user_image" />
		</template>
	</Autocomplete>
</template>
