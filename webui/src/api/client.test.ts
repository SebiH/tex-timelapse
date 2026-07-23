import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './client';

function jsonResponse(body: unknown, init: Partial<{ ok: boolean; status: number }> = {}): Response {
    return {
        ok: init.ok ?? true,
        status: init.status ?? 200,
        json: () => Promise.resolve(body),
    } as unknown as Response;
}

describe('api client', () => {
    beforeEach(() => {
        vi.restoreAllMocks();
    });

    it('listProjects issues a GET and unwraps the projects payload', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, projects: ['a', 'b'] }));
        vi.stubGlobal('fetch', fetchMock);

        const projects = await api.listProjects();

        expect(fetchMock).toHaveBeenCalledWith('/api/projects');
        expect(projects).toEqual(['a', 'b']);
    });

    it('getProject requests the project-specific URL', async () => {
        const project = { name: 'demo', config: {}, snapshots: [] };
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, project }));
        vi.stubGlobal('fetch', fetchMock);

        const result = await api.getProject('demo');

        expect(fetchMock).toHaveBeenCalledWith('/api/projects/demo');
        expect(result).toEqual(project);
    });

    it('updateProjectConfig POSTs the config as JSON', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true }));
        vi.stubGlobal('fetch', fetchMock);
        const config = { rows: 3 } as never;

        await api.updateProjectConfig('demo', config);

        expect(fetchMock).toHaveBeenCalledWith('/api/projects/demo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config }),
        });
    });

    it('startRender POSTs the output basename and unwraps the job', async () => {
        const job = { id: 'job1', project: 'demo', output: 'demo', status: 'running' };
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, job }));
        vi.stubGlobal('fetch', fetchMock);

        const result = await api.startRender('demo', 'demo');

        expect(fetchMock).toHaveBeenCalledWith('/api/projects/demo/jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ output: 'demo' }),
        });
        expect(result).toEqual(job);
    });

    it('startRender rejects with the server error when the job could not be created', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: false, error: 'already running' }));
        vi.stubGlobal('fetch', fetchMock);

        await expect(api.startRender('demo', 'demo')).rejects.toThrow('already running');
    });

    it('getJob requests the job-specific URL and unwraps the job', async () => {
        const job = { id: 'job1', project: 'demo', output: 'demo', status: 'running' };
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, job }));
        vi.stubGlobal('fetch', fetchMock);

        const result = await api.getJob('job1');

        expect(fetchMock).toHaveBeenCalledWith('/api/jobs/job1');
        expect(result).toEqual(job);
    });

    it('getJob rejects when the job is unknown', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: false, error: 'not found' }, { status: 404 }));
        vi.stubGlobal('fetch', fetchMock);

        await expect(api.getJob('missing')).rejects.toThrow('not found');
    });

    it('cancelRender issues a DELETE against the job endpoint and unwraps the job', async () => {
        const job = { id: 'job1', project: 'demo', output: 'demo', status: 'cancelled' };
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, job }));
        vi.stubGlobal('fetch', fetchMock);

        const result = await api.cancelRender('job1');

        expect(fetchMock).toHaveBeenCalledWith('/api/jobs/job1', { method: 'DELETE' });
        expect(result).toEqual(job);
    });

    it('resetProject issues a GET against the reset endpoint', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true }));
        vi.stubGlobal('fetch', fetchMock);

        await api.resetProject('demo');

        expect(fetchMock).toHaveBeenCalledWith('/api/projects/demo/reset');
    });

    it('runSnapshot requests the per-commit run endpoint and unwraps the snapshot', async () => {
        const snapshot = { commit_sha: 'abc123' };
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, snapshot }));
        vi.stubGlobal('fetch', fetchMock);

        const result = await api.runSnapshot('demo', 'abc123');

        expect(fetchMock).toHaveBeenCalledWith('/api/projects/demo/snapshot/abc123/run');
        expect(result).toEqual(snapshot);
    });

    it('resetSnapshot omits the stage segment when no stage is given', async () => {
        const snapshot = { commit_sha: 'abc123' };
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, snapshot }));
        vi.stubGlobal('fetch', fetchMock);

        await api.resetSnapshot('demo', 'abc123');

        expect(fetchMock).toHaveBeenCalledWith('/api/projects/demo/snapshot/abc123/reset');
    });

    it('resetSnapshot appends and encodes the stage segment when given', async () => {
        const snapshot = { commit_sha: 'abc123' };
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: true, snapshot }));
        vi.stubGlobal('fetch', fetchMock);

        await api.resetSnapshot('demo', 'abc123', 'Compile LaTeX');

        expect(fetchMock).toHaveBeenCalledWith('/api/projects/demo/snapshot/abc123/reset/Compile%20LaTeX');
    });

    it('getSnapshotImageUrl builds the path without calling fetch', () => {
        const fetchMock = vi.fn();
        vi.stubGlobal('fetch', fetchMock);

        const url = api.getSnapshotImageUrl('demo', 'abc123', 'page-01.jpg');

        expect(url).toBe('/api/projects/demo/snapshot/abc123/image/page-01.jpg');
        expect(fetchMock).not.toHaveBeenCalled();
    });

    it('rejects with the server-provided error message when success is false', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: false, error: 'nope' }));
        vi.stubGlobal('fetch', fetchMock);

        await expect(api.listProjects()).rejects.toThrow('nope');
    });

    it('falls back to a generic message when success is false without an error field', async () => {
        const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ success: false }));
        vi.stubGlobal('fetch', fetchMock);

        await expect(api.listProjects()).rejects.toThrow('/api/projects');
    });

    it('surfaces the HTTP status when the body cannot be parsed as JSON', async () => {
        const response = {
            ok: false,
            status: 500,
            json: () => Promise.reject(new Error('not json')),
        } as unknown as Response;
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));

        await expect(api.listProjects()).rejects.toThrow('HTTP 500');
    });

    describe('importProject', () => {
        it('POSTs a multipart form with the name and file, and returns the project', async () => {
            const project = { name: 'demo', config: {}, snapshots: [] };
            const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ message: 'ok', project }, { ok: true, status: 200 }));
            vi.stubGlobal('fetch', fetchMock);
            const file = new File(['content'], 'source.zip');

            const result = await api.importProject('demo', file);

            expect(fetchMock).toHaveBeenCalledTimes(1);
            const [url, init] = fetchMock.mock.calls[0];
            expect(url).toBe('/api/import');
            expect(init.method).toBe('POST');
            expect(init.body).toBeInstanceOf(FormData);
            expect((init.body as FormData).get('name')).toBe('demo');
            expect((init.body as FormData).get('file')).toBe(file);
            expect(result).toEqual(project);
        });

        it('rejects with the server error when the response has no success envelope but an error field', async () => {
            const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ error: 'bad zip' }, { ok: false, status: 400 }));
            vi.stubGlobal('fetch', fetchMock);

            await expect(api.importProject('demo', new File(['x'], 'x.zip'))).rejects.toThrow('bad zip');
        });

        it('rejects with a generic message when the response is not ok and unparsable', async () => {
            const response = {
                ok: false,
                status: 500,
                json: () => Promise.reject(new Error('not json')),
            } as unknown as Response;
            vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));

            await expect(api.importProject('demo', new File(['x'], 'x.zip'))).rejects.toThrow('Failed to import project');
        });
    });
});
