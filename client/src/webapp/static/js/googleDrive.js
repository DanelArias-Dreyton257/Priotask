/*
 * Talks to the Google Drive REST API directly from the browser using an
 * OAuth access token - analogous to api.js, but for Google's API instead of
 * Priotask's own. Kept separate from api.js because it is a different
 * transport entirely (no bearer token, no JSON error envelope) and the
 * server is never involved: the backup file never passes through Priotask's
 * own API beyond the plain export/import JSON payload (see
 * ApiClient.exportBackup/importBackup in api.js).
 *
 * Uses the `drive.appdata` scope, which only grants access to a hidden
 * per-app folder invisible in the user's normal Drive UI - the right shape
 * for an app-managed backup file that isn't meant to be browsed or shared.
 * This is a separate, incremental OAuth grant from the "Sign in with
 * Google" ID-token flow in app.js; it uses the same GIS script tag but a
 * different entry point (google.accounts.oauth2), and only ever requested
 * when the user actually clicks a backup/restore button.
 */
const DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.appdata";
const BACKUP_FILE_NAME = "priotask-backup.json";

let tokenClient = null;

function getTokenClient(clientId) {
    if (!tokenClient) {
        tokenClient = google.accounts.oauth2.initTokenClient({
            client_id: clientId,
            scope: DRIVE_SCOPE,
            callback: () => {}, // replaced per-request in requestAccessToken
        });
    }
    return tokenClient;
}

// Prompts the user (via a Google popup) to grant drive.appdata access and
// resolves with a short-lived OAuth access token. Must be called from
// within a user gesture (e.g. a click handler) or the browser may block
// the popup.
//
// Pass { silent: true } (v1.2.1, used for auto-restore-after-login) to
// request the token with prompt: 'none' instead - per the OAuth spec this
// means Google must not show any UI, and fails immediately if the user
// hasn't already granted drive.appdata access in a previous session. A
// timeoutMs safety net rejects the promise if the callback never fires at
// all, which silent flows can occasionally hit.
export function requestAccessToken(clientId, { silent = false, timeoutMs = 4000 } = {}) {
    return new Promise((resolve, reject) => {
        const client = getTokenClient(clientId);
        let settled = false;
        const settle = (fn, value) => {
            if (settled) return;
            settled = true;
            fn(value);
        };

        client.callback = (response) => {
            if (response.error) {
                settle(reject, new Error(`Google Drive access was not granted (${response.error}).`));
            } else {
                settle(resolve, response.access_token);
            }
        };
        client.error_callback = (error) => {
            settle(reject, new Error(error.message || "Google sign-in popup was closed before finishing."));
        };

        if (silent) {
            setTimeout(
                () => settle(reject, new Error("Silent Google Drive authorization timed out.")),
                timeoutMs,
            );
        }
        client.requestAccessToken(silent ? { prompt: "none" } : undefined);
    });
}

async function driveFetch(url, accessToken, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: { ...(options.headers || {}), Authorization: `Bearer ${accessToken}` },
    });
    if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`Google Drive request failed (${response.status}): ${text}`);
    }
    return response;
}

async function findBackupFile(accessToken) {
    const url = "https://www.googleapis.com/drive/v3/files?" + new URLSearchParams({
        spaces: "appDataFolder",
        q: `name='${BACKUP_FILE_NAME}' and trashed=false`,
        fields: "files(id,modifiedTime)",
    });
    const response = await driveFetch(url, accessToken);
    const data = await response.json();
    return data.files && data.files.length > 0 ? data.files[0] : null;
}

// Creates (first time) or overwrites (thereafter) the single backup file in
// the user's appDataFolder. Returns the modifiedTime Drive reports, mainly
// so the UI can show "last backed up at ...".
export async function uploadBackup(accessToken, backupData) {
    const content = JSON.stringify(backupData);
    const existing = await findBackupFile(accessToken);

    if (existing) {
        const response = await driveFetch(
            `https://www.googleapis.com/upload/drive/v3/files/${existing.id}?uploadType=media`,
            accessToken,
            { method: "PATCH", headers: { "Content-Type": "application/json" }, body: content },
        );
        return response.json();
    }

    const boundary = "priotask-backup-boundary";
    const metadata = JSON.stringify({ name: BACKUP_FILE_NAME, parents: ["appDataFolder"] });
    const body =
        `--${boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n${metadata}\r\n` +
        `--${boundary}\r\nContent-Type: application/json\r\n\r\n${content}\r\n` +
        `--${boundary}--`;
    const response = await driveFetch(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
        accessToken,
        { method: "POST", headers: { "Content-Type": `multipart/related; boundary=${boundary}` }, body },
    );
    return response.json();
}

// Returns the parsed backup JSON, or null if no backup file exists yet in
// this Google account's appDataFolder.
export async function downloadBackup(accessToken) {
    const existing = await findBackupFile(accessToken);
    if (!existing) return null;
    const response = await driveFetch(
        `https://www.googleapis.com/drive/v3/files/${existing.id}?alt=media`,
        accessToken,
    );
    return response.json();
}
