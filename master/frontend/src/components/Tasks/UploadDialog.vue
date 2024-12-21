<template>
  <TransitionRoot as="template" :show="isOpen">
    <Dialog as="div" class="relative z-10" @close="closeDialog">
      <TransitionChild
        enter="ease-out duration-300"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-200"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
      </TransitionChild>

      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <TransitionChild
            enter="ease-out duration-300"
            enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            enter-to="opacity-100 translate-y-0 sm:scale-100"
            leave="ease-in duration-200"
            leave-from="opacity-100 translate-y-0 sm:scale-100"
            leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          >
            <DialogPanel class="relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6 dark:bg-gray-800">
              <div>
                <div class="mt-3 text-center sm:mt-5">
                  <DialogTitle as="h3" class="text-base font-semibold leading-6 text-gray-900 dark:text-white">
                    上传视频文件
                  </DialogTitle>
                  <div class="mt-2">
                    <div
                      class="mt-2 flex justify-center rounded-lg border border-dashed border-gray-900/25 px-6 py-10 dark:border-gray-600"
                      @dragover.prevent
                      @drop.prevent="handleDrop"
                    >
                      <div class="text-center">
                        <PhotoIcon class="mx-auto h-12 w-12 text-gray-300" aria-hidden="true" />
                        <div class="mt-4 flex text-sm leading-6 text-gray-600 dark:text-gray-400">
                          <label
                            for="file-upload"
                            class="relative cursor-pointer rounded-md bg-white font-semibold text-primary-600 focus-within:outline-none focus-within:ring-2 focus-within:ring-primary-600 focus-within:ring-offset-2 hover:text-primary-500 dark:bg-gray-800"
                          >
                            <span>上传文件</span>
                            <input
                              id="file-upload"
                              name="file-upload"
                              type="file"
                              class="sr-only"
                              accept="video/*"
                              @change="handleFileSelect"
                            />
                          </label>
                          <p class="pl-1">或拖放文件</p>
                        </div>
                        <p class="text-xs leading-5 text-gray-600 dark:text-gray-400">支持MP4, AVI等视频格式</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3">
                <button
                  type="button"
                  class="btn-primary sm:col-start-2"
                  @click="handleUpload"
                  :disabled="!selectedFile"
                >
                  上传
                </button>
                <button
                  type="button"
                  class="btn-secondary mt-3 sm:col-start-1 sm:mt-0"
                  @click="closeDialog"
                >
                  取消
                </button>
              </div>
            </DialogPanel>
          </TransitionChild>
        </div>
      </div>
    </Dialog>
  </TransitionRoot>
</template>

<script setup>
import { ref } from 'vue'
import {
  Dialog,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  TransitionRoot,
} from '@headlessui/vue'
import { PhotoIcon } from '@heroicons/vue/24/outline'

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  }
})

const emit = defineEmits(['close', 'upload'])

const selectedFile = ref(null)

const closeDialog = () => {
  selectedFile.value = null
  emit('close')
}

const handleFileSelect = (event) => {
  selectedFile.value = event.target.files[0]
}

const handleDrop = (event) => {
  selectedFile.value = event.dataTransfer.files[0]
}

const handleUpload = async () => {
  if (!selectedFile.value) return
  
  const formData = new FormData()
  formData.append('file', selectedFile.value)
  
  emit('upload', formData)
  closeDialog()
}
</script> 