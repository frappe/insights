<template>
	<LoginBox title="Log in to your account">
		<form class="flex flex-col space-y-3" @submit.prevent="makeLoginRequest">
			<Input
				label="Email"
				v-model="email"
				placeholder="johndoe@mail.com"
				:type="email !== 'Administrator' ? 'email' : 'text'"
			/>
			<Input label="Password" type="password" placeholder="•••••" v-model="password" />
			<ErrorMessage :error="errorMessage" class="!mt-2" />
			<Button
				variant="solid"
				:disabled="loggingIn"
				:loading="loggingIn"
				@click="makeLoginRequest"
			>
				Submit
			</Button>
		</form>
	</LoginBox>
</template>

<script setup>
import LoginBox from '@/components/LoginBox.vue'
import useAuthStore from '@/stores/authStore'
import { onMounted, ref } from '@vue/runtime-core'
import { useRoute, useRouter } from 'vue-router'

const auth = useAuthStore()

const loggingIn = ref(null)
const email = ref(null)
const password = ref(null)
const errorMessage = ref(null)
const redirectRoute = ref(null)

const route = useRoute()
const router = useRouter()
onMounted(() => {
	if (route?.query?.route) {
		redirectRoute.value = route.query.route
		router.replace({ query: null })
	}
})
const makeLoginRequest = async () => {
	if (!email.value || !password.value) {
		return
	}
	try {
		errorMessage.value = null
		loggingIn.value = true
		let res = await auth.login(email.value, password.value)
		if (res) {
			router.push(redirectRoute.value || '/')
		}
	} catch (error) {
		console.error(error)
		errorMessage.value = error.messages.join('\n')
	} finally {
		loggingIn.value = false
	}
}
</script>
