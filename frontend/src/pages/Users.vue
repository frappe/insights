<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 class="text-3xl font-medium text-gray-900">Users</h1>
				<div class="space-x-4">
					<Button variant="outline" iconLeft="plus" @click="showAddUserDialog = true">
						Add User
					</Button>
				</div>
			</div>
		</template>
		<template #main>
			<div class="flex flex-1 flex-col overflow-hidden">
				<div class="mb-4 flex flex-shrink-0 space-x-4">
					<Input type="text" placeholder="Full Name" v-model="search.full_name" />
				</div>
				<div class="flex flex-1 flex-col overflow-hidden rounded border">
					<!-- List Header -->
					<div
						class="flex flex-shrink-0 items-center justify-between border-b px-4 py-3 text-sm text-gray-600"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded border-gray-300" />
						</p>
						<p class="flex-1 flex-shrink-0">Full Name</p>
						<p class="flex-1 flex-shrink-0">Email</p>
						<p class="flex-1 flex-shrink-0">Teams</p>
						<p class="flex-1 flex-shrink-0">Last Active</p>
					</div>
					<ul
						role="list"
						v-if="users.list?.length > 0"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-auto"
					>
						<li
							v-for="user in filteredUsers"
							:key="user.name"
							@click="userToEdit = user.name"
						>
							<div
								class="group flex h-11 cursor-pointer items-center rounded px-4 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded border-gray-300" />
								</p>
								<p class="flex flex-1 flex-shrink-0 items-center justify-between">
									<span
										class="overflow-hidden text-ellipsis whitespace-nowrap text-sm font-medium text-gray-900"
									>
										{{ user.full_name }}
									</span>
									<Badge v-if="user.type == 'Admin'" theme="green" class="mr-6">
										{{ user.type }}
									</Badge>
								</p>
								<p
									class="flex-1 flex-shrink-0 overflow-hidden text-ellipsis whitespace-nowrap text-sm text-gray-600"
								>
									{{ user.email }}
								</p>
								<p
									class="hidden flex-1 flex-shrink-0 overflow-hidden whitespace-nowrap text-sm text-gray-600 lg:inline-block"
								>
									{{ user.teams.length > 0 ? user.teams.join(', ') : '-' }}
								</p>
								<p
									class="hidden flex-1 flex-shrink-0 overflow-hidden whitespace-nowrap text-sm text-gray-600 lg:inline-block"
								>
									{{ fromNow(user.last_active) || '-' }}
								</p>
							</div>
						</li>
					</ul>
				</div>
			</div>
		</template>
	</BasePage>

	<AddUserDialog v-if="showAddUserDialog" @close="showAddUserDialog = false"></AddUserDialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import { useUsers } from '@/utils/useUsers.js'
import { computed, inject, reactive, ref } from 'vue'
import AddUserDialog from './AddUserDialog.vue'

const users = useUsers()
const userToEdit = ref(null)
const showAddUserDialog = ref(false)
const dayjs = inject('$dayjs')
const fromNow = (date) => date && dayjs(date).fromNow()

const search = reactive({
	full_name: '',
})
const filteredUsers = computed(() => {
	return users.list.filter((user) => {
		return user.full_name.toLowerCase().includes(search.full_name.toLowerCase())
	})
})
</script>
