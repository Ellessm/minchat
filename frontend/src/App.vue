<template>
  <div id="app">
    <!-- This will render the current route component -->
    <router-view />
  </div>
</template>

<script setup>
// No extra logic needed here.
// Vue Router automatically injects the current route component into <router-view>
</script>

<style>
/* Optional basic styling */
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
  margin-top: 60px;
}
</style>
