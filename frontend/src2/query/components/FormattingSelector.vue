<script setup lang="ts">
import { reactive, ref } from "vue";
import RadioGroupItem from "../../components/ui/RadioGroupItem.vue";
import RadioGroup from "../../components/ui/Radio.vue";
import { ColumnOption, GroupedColumnOption } from "../../types/query.types";
import { column } from "../helpers";
import { FormatGroupArgs, FormattingMode } from "./formatting_utils";
import FormatRule from "./FormatRule.vue";

const props = defineProps<{
  initialRule?: FormattingMode | null;
  columnOptions: ColumnOption[] | GroupedColumnOption[];
}>();

const emit = defineEmits<{
  close: [];
  select: [formatGroup: FormatGroupArgs];
}>();

const current = reactive<FormattingMode>(
  props.initialRule
    ? ({ ...props.initialRule } as FormattingMode)
    : ({ mode: "cell_rules", column: column(""), operator: "=", color: "red", value: 0 } as any)
);

const selectedFormatMode = ref<"cell_rules" | "color_scale">(
  current.mode === "color_scale" ? "color_scale" : "cell_rules"
);

function applyFormatting() {
  const group: FormatGroupArgs = { formats: [current], columns: [] };
  emit("select", group);
}
</script>

<template>
  <div class="min-w-[20rem] rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
    <div class="flex items-center justify-between pb-4">
      <h3 class="text-2xl font-semibold leading-6 text-gray-900">
        Conditional Formatting
      </h3>
      <Button variant="ghost" @click="() => emit('close')" icon="x" size="md">
      </Button>
    </div>
    <h3 class="text-sm text-gray-600 pb-3">
      Formatting Type
    </h3>
    <RadioGroup name="formatting-type" v-model="selectedFormatMode">
      <RadioGroupItem value="cell_rules">
        Highlight Cell
      </RadioGroupItem>
      <RadioGroupItem value="color_scale">
        Color Scale
      </RadioGroupItem>
    </RadioGroup>
    <FormatRule
      :modelValue="current"
      :columnOptions="props.columnOptions"
      :formatMode="selectedFormatMode"
      @update:modelValue="(val:any) => Object.assign(current, val)"
    />
    <div class="mt-6 flex items-center justify-end gap-2">
      <Button
        label="Cancel"
        variant="outline"
        @click="() => emit('close')"
      />
      <Button
        label="Apply Formatting"
        variant="solid"
        :disabled="!current?.column?.column_name"
        @click="applyFormatting"
      />
    </div>
  </div>
</template>
