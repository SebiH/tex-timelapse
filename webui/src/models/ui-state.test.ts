import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { TimelapseProject } from './project';
import type { TimelapseSnapshot } from './snapshot';

// ui-state.ts calls `io()` at module scope, and delegates to `api` for every
// network call - both need mocking before the module under test is imported.
vi.mock('socket.io-client', () => ({
    io: () => ({
        on: vi.fn(),
    }),
}));

vi.mock('@/api/client', () => ({
    api: {
        runSnapshot: vi.fn(),
        resetProject: vi.fn(),
        resetSnapshot: vi.fn(),
    },
}));

import { UIState } from './ui-state';
import { api } from '@/api/client';

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
});
