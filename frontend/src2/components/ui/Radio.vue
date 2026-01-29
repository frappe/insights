<template>
    <div
      class="flex flex-col gap-2"
      role="radiogroup"
      :aria-labelledby="labelId"
      v-bind="$attrs"
    >
      <slot />
    </div>
  </template>
  
  <script setup lang="ts">
  import { provide,computed } from 'vue'
  
  interface Props {
    modelValue?: string
    name?: string
    disabled?: boolean
  }
  
  const props = withDefaults(defineProps<Props>(), {
    disabled: false
  })
  
  const emit = defineEmits<{
    'update:modelValue': [value: string]
  }>()
  
  const labelId = computed(() => `radio-group-${Math.random().toString(36).substr(2, 9)}`)
  
  const updateValue = (value: string) => {
    if (!props.disabled) {
      emit('update:modelValue', value)
    }
  }
  
  provide('radioGroup', {
    modelValue: computed(() => props.modelValue),
    name: computed(() => props.name),
    disabled: computed(() => props.disabled),
    updateValue
  })
  </script>