import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { TimelapseProject } from './project';
import type { TimelapseSnapshot } from './snapshot';
import type { TimelapseJob } from './job';

// ui-state.ts calls `io()` at module scope, and delegates to `api` for every
// network call - both need mocking before the module under test is imported.
// `socketHandlers` captures every `socket.on(event, handler)` registration so
// tests can invoke a handler directly, the same way a real Socket.IO event
// would. It's built via `vi.hoisted` because `vi.mock` factories are hoisted
// above regular top-level statements - a plain `const` here would still be
// in its temporal dead zone when the factory closure below actually runs.
const socketHandlers: Record<string, (payload: never) => void> = vi.hoisted(() => ({}));
vi.mock('socket.io-client', () => ({
    io: () => ({
        on: (event: string, handler: (payload: never) => void) => {
            socketHandlers[event] = handler;
        },
    }),
}));

vi.mock('@/api/client', () => ({
    api: {
        runSnapshot: vi.fn(),
        resetProject: vi.fn(),
        resetSnapshot: vi.fn(),
        startRender: vi.fn(),
        cancelRender: vi.fn(),
    },
}));

import { UIState } from './ui-state';
import { api } from '@/api/client';

function makeJob(id: string, overrides: Partial<TimelapseJob> = {}): TimelapseJob {
    return {
        id,
        project: 'demo',
        output: 'demo',
        status: 'running',
        stage: '',
        stage_length: 0,
        stage_progress: 0,
        error: '',
        ...overrides,
    };
}

function makeSnapshot(commit_sha: string, overrides: Partial<TimelapseSnapshot> = {}): TimelapseSnapshot {
    return {
        commit_sha,
        commit_date: 0,
        main_tex_file: 'main.tex',
        status: 'Unknown',
        error: '',
        includes: [],
        gitDiff: '',
        changed_pages: [],
        pages: [],
        jobs: {},
        ...overrides,
    };
}

function makeProject(snapshots: TimelapseSnapshot[]): TimelapseProject {
    return {
        name: 'demo',
        config: {} as TimelapseProject['config'],
        snapshots,
    };
}

describe('UIState', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        UIState.project.next(null);
        UIState.currentSnapshot.next(null);
        UIState.activeJob.next(null);
    });

    describe('setProject', () => {
        it('publishes the project and selects its first snapshot as current', () => {
            const s1 = makeSnapshot('s1');
            const s2 = makeSnapshot('s2');
            const project = makeProject([s1, s2]);

            UIState.setProject(project);

            expect(UIState.project.value).toBe(project);
            expect(UIState.currentSnapshot.value).toBe(s1);
        });

        it('is a no-op when given the same project reference already stored', () => {
            const project = makeProject([makeSnapshot('s1')]);
            UIState.setProject(project);
            UIState.currentSnapshot.next(null);

            UIState.setProject(project);

            // setCurrentSnapshot-from-setProject only runs on an actual change,
            // so currentSnapshot should stay whatever we force-set it to above.
            expect(UIState.currentSnapshot.value).toBeNull();
        });
    });

    describe('setCurrentSnapshot', () => {
        it('selects the snapshot matching the given commit sha', () => {
            const s1 = makeSnapshot('s1');
            const s2 = makeSnapshot('s2');
            UIState.setProject(makeProject([s1, s2]));

            UIState.setCurrentSnapshot('s2');

            expect(UIState.currentSnapshot.value).toBe(s2);
        });

        it('sets null when no snapshot matches', () => {
            UIState.setProject(makeProject([makeSnapshot('s1')]));

            UIState.setCurrentSnapshot('does-not-exist');

            expect(UIState.currentSnapshot.value).toBeNull();
        });
    });

    describe('updateSnapshot', () => {
        it('replaces only the matching snapshot, leaving the others untouched', () => {
            const s1 = makeSnapshot('s1', { status: 'Unknown' });
            const s2 = makeSnapshot('s2', { status: 'Unknown' });
            const s3 = makeSnapshot('s3', { status: 'Unknown' });
            const project = makeProject([s1, s2, s3]);
            UIState.setProject(project);

            const updatedS2 = makeSnapshot('s2', { status: 'Completed' });
            UIState.updateSnapshot(project, updatedS2);

            const next = UIState.project.value;
            expect(next).not.toBeNull();
            expect(next!.snapshots).toHaveLength(3);
            expect(next!.snapshots[0]).toBe(s1);
            expect(next!.snapshots[1]).toBe(updatedS2);
            expect(next!.snapshots[1].status).toBe('Completed');
            expect(next!.snapshots[2]).toBe(s3);

            // original array must not have been mutated in place
            expect(project.snapshots[1]).toBe(s2);
        });

        it('updates currentSnapshot too when the updated snapshot is the current one', () => {
            const s1 = makeSnapshot('s1');
            const s2 = makeSnapshot('s2');
            const project = makeProject([s1, s2]);
            UIState.setProject(project);
            UIState.setCurrentSnapshot('s2');

            const updatedS2 = makeSnapshot('s2', { status: 'Failed' });
            UIState.updateSnapshot(UIState.project.value!, updatedS2);

            expect(UIState.currentSnapshot.value).toBe(updatedS2);
        });

        it('leaves currentSnapshot alone when a different snapshot is updated', () => {
            const s1 = makeSnapshot('s1');
            const s2 = makeSnapshot('s2');
            const project = makeProject([s1, s2]);
            UIState.setProject(project);
            UIState.setCurrentSnapshot('s1');

            const updatedS2 = makeSnapshot('s2', { status: 'Failed' });
            UIState.updateSnapshot(UIState.project.value!, updatedS2);

            expect(UIState.currentSnapshot.value).toBe(s1);
        });
    });

    describe('compileSnapshot', () => {
        it('runs the snapshot via the API and folds the result back into the project', async () => {
            const s1 = makeSnapshot('s1');
            const project = makeProject([s1]);
            UIState.setProject(project);
            const compiled = makeSnapshot('s1', { status: 'Completed' });
            vi.mocked(api.runSnapshot).mockResolvedValue(compiled);

            const ok = await UIState.compileSnapshot('s1');

            expect(ok).toBe(true);
            expect(api.runSnapshot).toHaveBeenCalledWith('demo', 's1');
            expect(UIState.project.value!.snapshots[0]).toBe(compiled);
        });

        it('returns false and does not throw when there is no current project', async () => {
            const ok = await UIState.compileSnapshot('s1');
            expect(ok).toBe(false);
            expect(api.runSnapshot).not.toHaveBeenCalled();
        });

        it('returns false when the API call rejects', async () => {
            UIState.setProject(makeProject([makeSnapshot('s1')]));
            vi.mocked(api.runSnapshot).mockRejectedValue(new Error('boom'));

            const ok = await UIState.compileSnapshot('s1');

            expect(ok).toBe(false);
        });
    });

    describe('resetSnapshot', () => {
        it('resets via the API and folds the result back into the project', async () => {
            UIState.setProject(makeProject([makeSnapshot('s1')]));
            const reset = makeSnapshot('s1', { status: 'Unknown' });
            vi.mocked(api.resetSnapshot).mockResolvedValue(reset);

            const ok = await UIState.resetSnapshot('s1', 'Compile LaTeX');

            expect(ok).toBe(true);
            expect(api.resetSnapshot).toHaveBeenCalledWith('demo', 's1', 'Compile LaTeX');
        });

        it('returns false when there is no current project', async () => {
            const ok = await UIState.resetSnapshot('s1');
            expect(ok).toBe(false);
        });
    });

    describe('resetProjectSnapshots', () => {
        it('resets every snapshot to Unknown with empty pages', async () => {
            const s1 = makeSnapshot('s1', { status: 'Completed', pages: ['page-01.jpg'] });
            const s2 = makeSnapshot('s2', { status: 'Failed', pages: ['page-01.jpg'] });
            const project = makeProject([s1, s2]);
            UIState.setProject(project);
            vi.mocked(api.resetProject).mockResolvedValue(undefined);

            await UIState.resetProjectSnapshots(project);

            expect(api.resetProject).toHaveBeenCalledWith('demo');
            const next = UIState.project.value!;
            expect(next.snapshots).toHaveLength(2);
            for (const snapshot of next.snapshots) {
                expect(snapshot.status).toBe('Unknown');
                expect(snapshot.pages).toEqual([]);
            }
        });
    });

    describe('startRender', () => {
        it('starts a render via the API and publishes the returned job', async () => {
            const project = makeProject([makeSnapshot('s1')]);
            const job = makeJob('job1');
            vi.mocked(api.startRender).mockResolvedValue(job);

            const result = await UIState.startRender(project, 'demo');

            expect(api.startRender).toHaveBeenCalledWith('demo', 'demo');
            expect(result).toEqual(job);
            expect(UIState.activeJob.value).toEqual(job);
        });

        it('returns null and does not throw when the API call rejects', async () => {
            const project = makeProject([makeSnapshot('s1')]);
            vi.mocked(api.startRender).mockRejectedValue(new Error('boom'));

            const result = await UIState.startRender(project, 'demo');

            expect(result).toBeNull();
            expect(UIState.activeJob.value).toBeNull();
        });
    });

    describe('cancelRender', () => {
        it('returns false and does not call the API when there is no active job', async () => {
            const ok = await UIState.cancelRender();

            expect(ok).toBe(false);
            expect(api.cancelRender).not.toHaveBeenCalled();
        });

        it('cancels the active job via the API and publishes the returned job', async () => {
            UIState.activeJob.next(makeJob('job1', { status: 'running' }));
            const cancelled = makeJob('job1', { status: 'cancelled' });
            vi.mocked(api.cancelRender).mockResolvedValue(cancelled);

            const ok = await UIState.cancelRender();

            expect(ok).toBe(true);
            expect(api.cancelRender).toHaveBeenCalledWith('job1');
            expect(UIState.activeJob.value).toEqual(cancelled);
        });

        it('returns false when the API call rejects', async () => {
            UIState.activeJob.next(makeJob('job1'));
            vi.mocked(api.cancelRender).mockRejectedValue(new Error('boom'));

            const ok = await UIState.cancelRender();

            expect(ok).toBe(false);
        });
    });

    describe('socket handlers', () => {
        it('stage updates activeJob stage/stage_length and resets stage_progress when the job matches', () => {
            UIState.activeJob.next(makeJob('job1', { stage: 'old', stage_length: 1, stage_progress: 0.5 }));

            socketHandlers['stage']({ job: 'job1', stage: 'Compile LaTeX', length: 10 } as never);

            expect(UIState.activeJob.value).toEqual(makeJob('job1', {
                stage: 'Compile LaTeX',
                stage_length: 10,
                stage_progress: 0,
            }));
        });

        it('stage is ignored when it belongs to a different job', () => {
            const job = makeJob('job1', { stage: 'old', stage_length: 1, stage_progress: 0.5 });
            UIState.activeJob.next(job);

            socketHandlers['stage']({ job: 'other-job', stage: 'Compile LaTeX', length: 10 } as never);

            expect(UIState.activeJob.value).toEqual(job);
        });

        it('stage creates a fresh activeJob when none is set yet', () => {
            UIState.setProject(makeProject([makeSnapshot('s1')]));

            socketHandlers['stage']({ job: 'job1', stage: 'Compile LaTeX', length: 10 } as never);

            expect(UIState.activeJob.value).toEqual(makeJob('job1', {
                project: 'demo',
                output: '',
                stage: 'Compile LaTeX',
                stage_length: 10,
                stage_progress: 0,
            }));
        });

        it('set_progress updates activeJob.stage_progress when the job matches', () => {
            UIState.activeJob.next(makeJob('job1', { stage_progress: 0 }));

            socketHandlers['set_progress']({ job: 'job1', set: 0.42 } as never);

            expect(UIState.activeJob.value?.stage_progress).toBe(0.42);
        });

        it('set_progress is ignored when there is no active job', () => {
            socketHandlers['set_progress']({ job: 'job1', set: 0.42 } as never);

            expect(UIState.activeJob.value).toBeNull();
        });

        it('set_progress is ignored when it belongs to a different job', () => {
            const job = makeJob('job1', { stage_progress: 0 });
            UIState.activeJob.next(job);

            socketHandlers['set_progress']({ job: 'other-job', set: 0.9 } as never);

            expect(UIState.activeJob.value).toEqual(job);
        });
    });
});
