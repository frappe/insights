<script setup lang="ts">
import { Avatar } from 'frappe-ui'
import session from '../session'
import { computed, ref } from 'vue'
import useUserStore from '../users/users'

const user = ref({ ...session.user })

const updateDisabled = computed(() => {
	return (
		user.value.first_name === session.user.first_name &&
		user.value.last_name === session.user.last_name
	)
})

const userStore = useUserStore()
function update() {
	if (updateDisabled.value) return

	userStore
		.updateUser(session.user.email, {
			first_name: user.value.first_name,
			last_name: user.value.last_name,
		})
		.then(() => {
			session.user.first_name = user.value.first_name
			session.user.last_name = user.value.last_name
		})
}
</script>

<template>
	<div class="flex w-full flex-col gap-6 p-8 px-10">
		<h1 class="text-xl font-semibold">Profile</h1>
		<div class="flex items-start gap-4">
			<div class="relative flex flex-col items-center justify-between gap-2">
				<Avatar class="!h-15 !w-15" :image="user.user_image" :label="user.full_name" />
			</div>
			<div class="flex h-15 flex-col justify-center gap-1">
				<span class="text-lg font-semibold">{{ user.full_name }}</span>
				<span class="text-base text-gray-700">{{ user.email }}</span>
			</div>
		</div>
		<div class="flex w-full flex-col gap-4">
			<div class="flex gap-6">
				<FormControl
					v-model="user.first_name"
					label="First Name"
					autocomplete="off"
					class="flex-1"
				/>
				<FormControl
					autocomplete="off"
					class="flex-1"
					label="Last Name"
					v-model="user.last_name"
				/>
			</div>
			<div class="flex gap-6">
				<FormControl
					autocomplete="off"
					class="flex-1"
					label="Email"
					:modelValue="user.email"
					:disabled="true"
				/>
				<FormControl
					autocomplete="off"
					class="flex-1"
					label="New Password"
					type="password"
					disabled
				/>
			</div>
			<div class="flex justify-end">
				<Button
					label="Update"
					variant="solid"
					:loading="userStore.updatingUser"
					:disabled="updateDisabled"
					@click="update"
				/>
			</div>
		</div>
	</div>
</template>
