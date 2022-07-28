<template>
	<div class="flex flex-col items-center py-24">
		<div
			class="flex h-full w-[38rem] flex-col space-y-6 rounded-md border bg-white p-8 py-6 text-base shadow-md"
		>
			<div class="">
				<h1 class="text-4xl font-medium leading-relaxed text-gray-900">
					Welcome to Frappe Insights!
				</h1>
				<p class="font-light text-gray-600">
					{{
						connectDB
							? 'Connect to your database'
							: demoDB
							? 'Select a demo database'
							: 'Connect to your database or explore with a dummy database'
					}}
				</p>
			</div>
			<div v-if="!connectDB && !demoDB" class="-mx-2 flex">
				<div
					class="m-2 flex w-1/2 flex-col items-center rounded-md border border-dashed border-gray-300 p-4"
				>
					<p class="text-xl leading-loose">Connect to your database</p>
					<p class="mb-3 text-center text-sm font-light text-gray-600">
						You can connect to a database hosted over network or hosted locally
					</p>
					<Button appearance="white" @click="connectDB = true">Connect</Button>
				</div>
				<div
					class="m-2 flex w-1/2 flex-col items-center rounded-md border border-dashed border-gray-300 p-4"
				>
					<p class="text-xl leading-loose">Explore a dummy database</p>
					<p class="mb-3 text-center text-sm font-light text-gray-600">
						You can explore the app with a dummy database and choose to connect later
					</p>
					<Button
						appearance="white"
						@click="createDemoDb.submit()"
						:loading="createDemoDb.loading"
					>
						{{ exploreText }}
					</Button>
				</div>
			</div>
			<div v-if="connectDB">
				<AddDatabase @close="connectDB = false" />
			</div>
		</div>
	</div>
</template>

<script setup>
import AddDatabase from '@/components/Onboarding/AddDatabase.vue'

import { useRouter } from 'vue-router'
import { computed, ref, nextTick } from 'vue'
import { createResource } from 'frappe-ui'

const connectDB = ref(false)
const demoDB = ref(false)

const exploreText = computed(() => (createDemoDb.loading ? 'Setting Up...' : 'Explore'))
const router = useRouter()
const createDemoDb = createResource({
	method: 'insights.api.onboarding.setup_demo',
	onSuccess: () => {
		localStorage.removeItem('isOnboarded')
		nextTick(() => router.push('/'))
	},
})
</script>
