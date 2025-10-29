import { createRouter, createWebHistory } from "vue-router";
import LoginForm from "./components/LoginForm.vue";
import RegisterForm from "./components/RegisterForm.vue";
import ChatView from "./components/ChatView.vue";

const routes = [
  { path: "/", component: LoginForm },
  { path: "/register", component: RegisterForm },
  { path: "/chat/:username", component: ChatView, props: true },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Prevent entering /chat without a username; use localStorage fallback when available
router.beforeEach((to, from, next) => {
  if (to.path.startsWith("/chat")) {
    const usernameParam = to.params.username;
    const saved = localStorage.getItem("username");
    if ((!usernameParam || usernameParam === "") && !saved) {
      return next({ path: "/" });
    }
    // If no param but saved username exists, redirect to that chat path
    if ((!usernameParam || usernameParam === "") && saved) {
      return next({ path: `/chat/${saved}` });
    }
  }
  next();
});

export default router;