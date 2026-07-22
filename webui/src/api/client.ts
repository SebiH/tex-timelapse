// Single source of truth for every `/api/...` call the web UI makes.
//
// The Flask server wraps almost all responses in `{ success: boolean, error?:
// string, ...payload }` (see `tex_timelapse/webserver.py`, read-only from this
// side of the codebase). `/api/import` is the one exception - it responds
// with `{ message, project }` on success and `{ error }` on failure, with no
// `success` field at all - so it gets its own parsing below instead of
// reusing the envelope helpers.
//
// Keep this module thin: a later phase turns `/run` into async job endpoints,
// and callers should only need their call sites touched, not this file's
// shape, when that lands.

import { TimelapseProject } from '@/models/project';
import { TimelapseSnapshot } from '@/models/snapshot';
import { TimelapseConfig } from '@/models/config';

type ApiSuccess<T> = { success: true } & T;
type ApiFailure = { success: false; error?: string };
type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

async function parseEnvelope<T>(response: Response, path: string): Promise<T> {
    let data: ApiResponse<T>;
    try {
        data = await response.json();
    } catch {
        throw new Error(`Request to ${path} failed (HTTP ${response.status})`);
    }

    if (!data.success) {
        throw new Error(data.error || `Request to ${path} failed`);
    }

    // `data` is narrowed to `ApiSuccess<T>` here, i.e. `{ success: true } & T`;
    // the extra `success` field is harmless to callers, who only destructure
    // the payload fields they care about.
    return data;
}

async function get<T>(path: string): Promise<T> {
    const response = await fetch(path);
    return parseEnvelope<T>(response, path);
}

async function post<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return parseEnvelope<T>(response, path);
}

export const api = {
    async listProjects(): Promise<string[]> {
        const { projects } = await get<{ projects: string[] }>('/api/projects');
        return projects;
    },

    async getProject(name: string): Promise<TimelapseProject> {
        const { project } = await get<{ project: TimelapseProject }>(`/api/projects/${name}`);
        return project;
    },

    async updateProjectConfig(name: string, config: TimelapseConfig): Promise<void> {
        await post<object>(`/api/projects/${name}`, { config });
    },

    async runProject(name: string): Promise<void> {
        await get<object>(`/api/projects/${name}/run`);
    },

    async resetProject(name: string): Promise<void> {
        await get<object>(`/api/projects/${name}/reset`);
    },

    async runSnapshot(projectName: string, commitSha: string): Promise<TimelapseSnapshot> {
        const { snapshot } = await get<{ snapshot: TimelapseSnapshot }>(
            `/api/projects/${projectName}/snapshot/${commitSha}/run`
        );
        return snapshot;
    },

    // `stage` is an action name as reported by the server (e.g. 'Compile LaTeX');
    // that stage and every later one are reset. Omit it to reset all stages.
    async resetSnapshot(projectName: string, commitSha: string, stage?: string): Promise<TimelapseSnapshot> {
        const path = `/api/projects/${projectName}/snapshot/${commitSha}/reset`;
        const { snapshot } = await get<{ snapshot: TimelapseSnapshot }>(
            stage ? `${path}/${encodeURIComponent(stage)}` : path
        );
        return snapshot;
    },

    // Not a fetch - just the one place that knows how a snapshot page image
    // URL is built, so callers don't hand-roll the path.
    getSnapshotImageUrl(projectName: string, commitSha: string, imageBasename: string): string {
        return `/api/projects/${projectName}/snapshot/${commitSha}/image/${imageBasename}`;
    },

    async importProject(name: string, file: File): Promise<TimelapseProject> {
        const formData = new FormData();
        formData.append('name', name);
        formData.append('file', file);

        const response = await fetch('/api/import', {
            method: 'POST',
            body: formData,
        });

        let data: { message: string; project: TimelapseProject } | { error: string } | null = null;
        try {
            data = await response.json();
        } catch {
            // fall through to the generic error below
        }

        if (!response.ok || !data || 'error' in data) {
            throw new Error((data && 'error' in data && data.error) || 'Failed to import project');
        }

        return data.project;
    },
};
