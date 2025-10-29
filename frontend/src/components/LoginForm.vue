<template>
  <div class="login-form">
    <h2>Login</h2>
    <form @submit.prevent="login">
      <input v-model="username" placeholder="Username" required />
      <input v-model="password" type="password" placeholder="Password" required />
      <button type="submit">Login</button>
    </form>
    <p>
      Don't have an account? <router-link to="/register">Register here</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import axios from "axios";
import { useRouter } from "vue-router";

const username = ref("");
const password = ref("");
const router = useRouter();

async function login() {
  try {
    await axios.post("http://localhost:8000/auth/login", {
      username: username.value,
      password: password.value,
    });
    router.push(`/chat/${username.value}`);
  } catch (err) {
    alert("Login failed");
    console.error(err);
  }
}
</script>

<style scoped>
.login-form { max-width: 400px; margin: auto; }
input { display: block; margin: 10px 0; width: 100%; padding: 8px; }
button { padding: 8px 16px; }
</style>
