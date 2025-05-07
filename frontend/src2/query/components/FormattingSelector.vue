<script setup lang="ts">
import { PlusIcon } from "lucide-vue-next";
import { computed, reactive } from "vue";
import { copy, flattenOptions } from "../../helpers";
import {
  ColumnOption,
  GroupedColumnOption,
} from "../../types/query.types";
import { column } from "../helpers";
import { FormatGroupArgs, FormattingMode } from "./formatting_utils";
import FormatRule from "./FormatRule.vue";

const props = defineProps<{
  formatMode?: FormattingMode;
  formatGroup?: FormatGroupArgs;
  columnOptions: ColumnOption[] | GroupedColumnOption[];
}>();

const emit = defineEmits({
  select: (args: FormatGroupArgs) => true,
  close: () => true,
});

const formatGroup = reactive<FormatGroupArgs>(
  props.formatGroup
    ? copy(props.formatGroup)
    : {
        columns: [],
        formats: [],
      },
);

function addFormat() {
  //show first column as placeholder
  const options = flattenOptions(props.columnOptions) as ColumnOption[];
  const firstColumn = options.length > 0 ? options[0].value : "";

  formatGroup.formats.push({
    mode: "cell_rules",
    column: column(firstColumn),
    operator: "=",
    color: "Red",
    value: 0,
  });
}

const areFormatsUpdated = computed(() => {
  if (!props.formatGroup) return true;
  return JSON.stringify(formatGroup) !== JSON.stringify(props.formatGroup);
});
</script>

<template>
  <div class="min-w-[36rem] rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
    <div class="flex items-center justify-between pb-4">
      <h3 class="text-2xl font-semibold leading-6 text-gray-900">
        Conditional Formatting
      </h3>
      <Button variant="ghost" @click="emit('close')" icon="x" size="md">
      </Button>
    </div>
    <div
      v-if="formatGroup.formats.length"
      v-for="(_, i) in formatGroup.formats"
      :key="i"
      id="formats-list"
      class="mb-3 flex items-start justify-between gap-2"
    >
      <div class="flex flex-1 items-start gap-2">
        <FormatRule
          v-if="'column' in formatGroup.formats[i]"
          :modelValue="formatGroup.formats[i]"
          :columnOptions="props.columnOptions"
          @update:modelValue="formatGroup.formats[i] = $event"
        />
      </div>
      <div class="flex h-full flex-shrink-0 items-start">
        <Dropdown
          placement="right"
          :button="{
            icon: 'more-horizontal',
            variant: 'ghost',
          }"
          :options="[
            {
              label: 'Remove',
              onClick: () => formatGroup.formats.splice(i, 1),
            },
          ]"
        />
      </div>
    </div>
    <div v-else class="mb-3 flex h-7 items-center px-0 text-sm text-gray-600">
      Empty - Click 'Add Format' to add conditional formatting
    </div>
    <div class="mt-2 flex items-center justify-between gap-2">
      <Button @click="addFormat" label="Add Format">
        <template #prefix>
          <PlusIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
        </template>
      </Button>
      <div class="flex items-center gap-2">
        <Button
          label="Clear"
          variant="outline"
          @click="formatGroup.formats = []"
        />
        <Button
          label="Apply Formatting"
          variant="solid"
          :disabled="!areFormatsUpdated"
          @click="
            () => {
              emit('select', formatGroup);
            }
          "
        />
      </div>
    </div>
  </div>
</template>
