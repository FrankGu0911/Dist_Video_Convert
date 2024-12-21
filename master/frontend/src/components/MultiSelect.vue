<template>
  <div class="relative">
    <div 
      class="min-h-[38px] w-full rounded-md border border-gray-300 bg-white px-2 py-1 shadow-sm dark:border-gray-600 dark:bg-gray-700 focus-within:border-primary-500 focus-within:ring-1 focus-within:ring-primary-500"
      @click="isOpen = true"
    >
      <div class="flex flex-wrap gap-1">
        <span 
          v-for="value in modelValue" 
          :key="value" 
          :class="[
            getOptionClass(value),
            'inline-flex items-center gap-1 rounded px-2 py-0.5 text-sm font-medium'
          ]"
        >
          {{ getOptionLabel(value) }}
          <button
            type="button"
            class="inline-flex rounded-sm hover:bg-opacity-75"
            @click.stop="removeValue(value)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </span>
        <input
          type="text"
          class="flex-1 border-none bg-transparent p-0.5 outline-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
          :placeholder="modelValue.length ? '' : placeholder"
          readonly
        />
      </div>
    </div>

    <div 
      v-show="isOpen"
      class="absolute z-10 mt-1 w-full overflow-auto rounded-md bg-white py-1 shadow-lg dark:bg-gray-800"
      style="max-height: 15rem;"
    >
      <div 
        v-for="option in options"
        :key="option.value"
        class="flex cursor-pointer items-center px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-700"
        @click="toggleOption(option)"
      >
        <div 
          class="mr-3 flex h-5 w-5 items-center justify-center rounded border border-gray-300 dark:border-gray-600"
          :class="{ 'border-primary-500 bg-primary-500 dark:border-primary-500 dark:bg-primary-500': isSelected(option.value) }"
        >
          <svg 
            v-if="isSelected(option.value)"
            class="h-4 w-4 text-white" 
            viewBox="0 0 20 20" 
            fill="currentColor"
          >
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </div>
        <span class="text-sm text-gray-900 dark:text-gray-300">{{ option.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => []
  },
  options: {
    type: Array,
    required: true
  },
  placeholder: {
    type: String,
    default: '请选择'
  }
})

const emit = defineEmits(['update:modelValue'])
const isOpen = ref(false)

const getOptionLabel = (value) => {
  const option = props.options.find(opt => opt.value === value)
  return option ? option.label : ''
}

const isSelected = (value) => {
  return props.modelValue.includes(value)
}

const toggleOption = (option) => {
  const newValue = [...props.modelValue]
  const index = newValue.indexOf(option.value)
  if (index === -1) {
    newValue.push(option.value)
  } else {
    newValue.splice(index, 1)
  }
  emit('update:modelValue', newValue)
}

const removeValue = (value) => {
  const newValue = props.modelValue.filter(v => v !== value)
  emit('update:modelValue', newValue)
}

const closeOnClickOutside = (e) => {
  if (!e.target.closest('.relative')) {
    isOpen.value = false
  }
}

const getOptionClass = (value) => {
  const option = props.options.find(opt => opt.value === value)
  return option?.class || 'bg-primary-100 text-primary-700 dark:bg-primary-900/50 dark:text-primary-300'
}

onMounted(() => {
  document.addEventListener('click', closeOnClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', closeOnClickOutside)
})
</script> 