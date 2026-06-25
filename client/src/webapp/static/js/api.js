/*
 * Thin wrapper around the Phase 4 REST API (server/src/api/). Knows the
 * routes and JSON shapes (TaskDTO/UserDTO) but has no UI logic of its own -
 * analogous to the server-side RemoteFacade (server/src/remote/RemoteFacade.py).
 */
import { TokenStore } from "./session.js";

class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
    }
}

export class ApiClient {
    constructor(baseUrl) {
        this.baseUrl = baseUrl.replace(/\/$/, "");
    }

    async _request(method, path, { body, auth = false } = {}) {
        const headers = {};
        if (body !== undefined) headers["Content-Type"] = "application/json";
        if (auth) {
            const token = TokenStore.getToken();
            if (token) headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await fetch(`${this.baseUrl}${path}`, {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });

        if (response.status === 204) return null;

        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new ApiError(data.error || `request failed (${response.status})`, response.status);
        }
        return data;
    }

    register(username, password, email) {
        return this._request("POST", "/api/users", { body: { username, password, email } });
    }

    async login(username, password) {
        const { token } = await this._request("POST", "/api/auth/login", { body: { username, password } });
        TokenStore.setToken(token);
        return token;
    }

    async logout() {
        await this._request("POST", "/api/auth/logout", { auth: true });
        TokenStore.clearToken();
    }

    listTasks() {
        return this._request("GET", "/api/tasks", { auth: true });
    }

    createTask(task) {
        return this._request("POST", "/api/tasks", { body: task, auth: true });
    }

    updateTask(taskId, task) {
        return this._request("PUT", `/api/tasks/${taskId}`, { body: task, auth: true });
    }

    completeTask(taskId) {
        return this._request("POST", `/api/tasks/${taskId}/complete`, { auth: true });
    }

    deleteTask(taskId) {
        return this._request("DELETE", `/api/tasks/${taskId}`, { auth: true });
    }

    getTodayPlan(hours) {
        const query = hours !== undefined ? `?hours=${encodeURIComponent(hours)}` : "";
        return this._request("GET", `/api/plan/today${query}`, { auth: true });
    }
}

export { ApiError };
