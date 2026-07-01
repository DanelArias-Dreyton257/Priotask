/*
 * Persists the bearer token issued by /api/auth/login in localStorage, so a
 * page refresh doesn't log the user out. Analogous to the server-side
 * TokenManager (server/src/remote/TokenManager.py), but browser-backed.
 */
const TOKEN_KEY = "priotask.token";
const USERNAME_KEY = "priotask.username";

export const TokenStore = {
    getToken() {
        return localStorage.getItem(TOKEN_KEY);
    },

    setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    },

    getUsername() {
        return localStorage.getItem(USERNAME_KEY);
    },

    setUsername(username) {
        localStorage.setItem(USERNAME_KEY, username);
    },

    clearToken() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USERNAME_KEY);
    },
};
