<script setup lang="ts">
import { TextInput } from 'frappe-ui';

const modelValue = defineModel({
    type: String,
    required: true,
    default: '',
});

</script>

<template>
    <TextInput
        v-bind="$attrs"
        type="text"
        class="w-full"
        variant="subtle"
        autocomplete="off"
        :model-value="modelValue"
        @keydown.enter="modelValue = $event.target.value"
        @blur="modelValue = $event.target.value"
    />					
</template>