import { TimelapseProject } from './project';
import { BehaviorSubject, Subject } from 'rxjs';
import { TimelapseSnapshot } from './snapshot';
import { TimelapseJob } from './job';
import { io } from 'socket.io-client';
import { api } from '@/api/client';

export const UIState = {
    project: new BehaviorSubject<TimelapseProject | null>(null),
    currentSnapshot: new BehaviorSubject<TimelapseSnapshot | null>(null),
    // The in-flight (or most recently seen) render job, if any. Populated by
    // `startRender` and kept current by the `stage`/`set_progress` socket
    // handlers below. There's no socket event for "job done" - the backend
    // only pushes stage/progress - so nothing here clears it automatically;
    // callers that care (e.g. after cancelling) clear or replace it explicitly.
    activeJob: new BehaviorSubject<TimelapseJob | null>(null),

    setProject(project: TimelapseProject) {
        if (project !== this.project.value) {
            this.project.next(project);
            for (const snapshot of project?.snapshots || []) {
                snapshot.pages = snapshot.pages.sort();
            }

            this.currentSnapshot.next(project?.snapshots[0]);
        }
    },

    setCurrentSnapshot(commit_sha: string) {
        this.currentSnapshot.next(this.project.value?.snapshots.find(s => s.commit_sha === commit_sha) || null);
    },

    async compileSnapshot(commit_sha: string) {
        const project = this.project.value;
        if (!project) return false;

        try {
            const snapshot = await api.runSnapshot(project.name, commit_sha);
            this.updateSnapshot(project, snapshot);
            return true;
        } catch (e) {
            console.error(e);
            return false;
        }
    },

    async resetProjectSnapshots(project: TimelapseProject) {
        await api.resetProject(project.name);

        const snapshots: TimelapseSnapshot[] = UIState.project.value?.snapshots.map((s: TimelapseSnapshot) => {
            return { ...s, status: 'Unknown', pages: [] };
        }) || [];

        if (UIState.project.value) {
            UIState.project.value.snapshots = snapshots;
        }

        UIState.setProject({ ...project, snapshots });

        for (const snapshot of snapshots) {
            snapshotUpdates.next(snapshot);
        }
    },

    updateSnapshot(project: TimelapseProject, snapshot: TimelapseSnapshot) {
        snapshot.pages = snapshot.pages.sort();
        const index = project.snapshots.findIndex(s => s.commit_sha === snapshot.commit_sha);
        const nextProject: TimelapseProject = {
            ...project,
            snapshots: [
                ...project.snapshots.slice(0, index),
                snapshot as TimelapseSnapshot,
                ...project.snapshots.slice(index + 1)
            ]
        };
        this.project.next(nextProject);

        // update current snapshot if it's the same (since it might have changed)
        if (this.currentSnapshot.value?.commit_sha === snapshot.commit_sha) {
            this.currentSnapshot.next(snapshot as TimelapseSnapshot);
        }
    },

    // `stage` is an action name as reported by the server (e.g. 'Compile LaTeX');
    // that stage and every later one are reset. Omit it to reset all stages.
    async resetSnapshot(commit_sha: string, stage?: string) {
        const project = this.project.value;
        if (!project) return false;

        try {
            const snapshot = await api.resetSnapshot(project.name, commit_sha, stage);
            this.updateSnapshot(project, snapshot);
            return true;
        } catch (e) {
            console.error(e);
            return false;
        }
    },

    async startRender(project: TimelapseProject, output: string): Promise<TimelapseJob | null> {
        try {
            const job = await api.startRender(project.name, output);
            this.activeJob.next(job);
            return job;
        } catch (e) {
            console.error(e);
            return null;
        }
    },

    async cancelRender(): Promise<boolean> {
        const job = this.activeJob.value;
        if (!job) return false;

        try {
            const cancelled = await api.cancelRender(job.id);
            this.activeJob.next(cancelled);
            return true;
        } catch (e) {
            console.error(e);
            return false;
        }
    }
};

const socket = io();
const snapshotUpdates = new Subject<TimelapseSnapshot>();
export const snapshotUpdates$ = snapshotUpdates.asObservable();

socket.on('stage', ({ job, stage, length }: { job: string, stage: string, length: number }) => {
    const current = UIState.activeJob.value;
    if (current !== null && current.id !== job) return;

    // No activeJob yet (e.g. a render started elsewhere, or a page reload
    // mid-render) but a stage event for it just arrived - fill in what we
    // know, borrowing the project name from the currently loaded project
    // since the event itself doesn't carry one.
    const base: TimelapseJob = current || {
        id: job,
        project: UIState.project.value?.name || '',
        output: '',
        status: 'running',
        stage: '',
        stage_length: 0,
        stage_progress: 0,
        error: '',
    };

    UIState.activeJob.next({ ...base, stage, stage_length: length, stage_progress: 0 });
});

socket.on('add_progress', ({ snapshot }: { snapshot: TimelapseSnapshot }) => {
    // const project = UIState.project.value;
    // if (project)
    //     UIState.updateSnapshot(project, snapshot);
    snapshotUpdates.next(snapshot);

    if (UIState.project.value?.snapshots) {
        const index = UIState.project.value.snapshots.findIndex(s => s.commit_sha === snapshot.commit_sha);
        if (index !== -1) {
            UIState.project.value.snapshots[index] = snapshot;
            UIState.project.next(UIState.project.value);
        }
    }

    if (UIState.currentSnapshot.value?.commit_sha === snapshot.commit_sha) {
        UIState.currentSnapshot.next(snapshot);
    }
});

socket.on('set_progress', ({ job, set }: { job: string, set: number }) => {
    const current = UIState.activeJob.value;
    if (current !== null && current.id === job) {
        UIState.activeJob.next({ ...current, stage_progress: set });
    }
});

socket.on('log', ({ job, msg, snapshot_sha }: { job: string, msg: string, snapshot_sha?: string | null }) => {
    // TODO
    console.log('log', job, msg, snapshot_sha);
});

