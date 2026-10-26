import { useCallback, useEffect, useState } from "react";
import { api, setAuthToken } from "../api.js";

const TOKEN_KEY = "furniture-store-token";

// localStorage can throw (private browsing, blocked storage), so wrap every access.
const readToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};
const writeToken = (token) => {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* login still works for this visit */
  }
};

// Custom hook: who is logged in, plus login / signup / logout.
export function useAuth() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true); // true while we validate a saved token

  const saveSession = useCallback(({ token, user }) => {
    setAuthToken(token);
    writeToken(token);
    setUser(user);
  }, []);

  const logout = useCallback(() => {
    setAuthToken(null);
    writeToken(null);
    setUser(null);
  }, []);

  // On first load, if a token was saved earlier, ask the server who it belongs to.
  useEffect(() => {
    const saved = readToken();
    if (!saved) {
      setChecking(false);
      return;
    }
    setAuthToken(saved);
    api
      .me()
      .then(setUser)
      .catch(logout) // expired or invalid token
      .finally(() => setChecking(false));
  }, [logout]);

  return {
    user,
    checking,
    login: async (email, password) => saveSession(await api.login(email, password)),
    signup: async (name, email, password) => saveSession(await api.signup(name, email, password)),
    logout,
  };
}
