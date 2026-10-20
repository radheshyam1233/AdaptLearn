// src/auth.jsx
// Keeps track of who is logged in and shares it with every page (React Context).

import { createContext, useContext, useState } from "react";
import { request } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Start from whatever was saved, so a page refresh keeps you logged in
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("user") || "null"));

  async function login(email, password) {
    const data = await request("/auth/login", { method: "POST", form: { username: email, password } });
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("user", JSON.stringify(data.user));
    setUser(data.user);
    return data.user;
  }

  async function register(name, email, password) {
    await request("/auth/register", { method: "POST", body: { name, email, password } });
    return login(email, password);   // log straight in after signing up
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Any component can call useAuth() to get { user, login, register, logout }
export function useAuth() {
  return useContext(AuthContext);
}
