<template>
  <div class="register-form">
    <h2>Register</h2>
    <form @submit.prevent="register">
      <input v-model="username" placeholder="Username" required />
      <input v-model="password" type="password" placeholder="Password" required />
      <button type="submit">Register</button>
    </form>
    <p>
      Already have an account? <router-link to="/">Login here</router-link>
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

async function register() {
  try {
    await axios.post("http://localhost:8000/auth/register", {
      username: username.value,
      password: password.value,
    });
    alert("Registration successful!");
    router.push("/");
  } catch (err) {
    alert("Registration failed");
    console.error(err);
  }
}
</script>

<style scoped>
.register-form { max-width: 400px; margin: auto; }
input { display: block; margin: 10px 0; width: 100%; padding: 8px; }
button { padding: 8px 16px; }
</style>
