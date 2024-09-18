<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import useUserStore, { User } from '../users/users'

const props = defineProps<{ hideUsers?: string[] }>()
const selectedUser = defineModel<User | null>()

const userStore = useUserStore()
const searchTxt = ref('')
watchEffect(() => {
	searchTxt.value = selectedUser.value?.email || ''
})
const filteredUsers = computed(() => {
	return userStore.users
		.filter((user) => {
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
		v-model="selectedUser"
		:hide-search="true"
		:options="filteredUsers"
		:autofocus="false"
	>
		<template #target="{ open }">
			<FormControl
				class="w-full"
				type="text"
				placeholder="Search by email or name"
				autocomplete="off"
				v-model="searchTxt"
				@update:modelValue="open"
				@focus="open"
			/>
		</template>

		<template #item-prefix="{ option }">
			<Avatar size="sm" :label="option.label" :image="option.user_image" />
		</template>
	</Autocomplete>
</template>
