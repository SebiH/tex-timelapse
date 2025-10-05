import { TimelapseProject } from './project';
import { BehaviorSubject, Subject } from 'rxjs';
import { TimelapseSnapshot } from './snapshot';
import { io } from 'socket.io-client';

export const UIState = {
    project: new BehaviorSubject<TimelapseProject | null>(null),
    currentSnapshot: new BehaviorSubject<TimelapseSnapshot | null>(null),

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

        const request = await fetch(`/api/projects/${project.name}/snapshot/${commit_sha}/run`);
        try {
            const response = await request.json();
            if (response.success) {
                this.updateSnapshot(project, response.snapshot as TimelapseSnapshot);
            } else {
                console.error(response.error);
            }

            return response.success as boolean;
        } catch (e) {
            console.error(e);
            return false;
        }
    },

    async resetProjectSnapshots(project: TimelapseProject) {
        return fetch(`/api/projects/${project.name}/reset`).then(async (response) => {
            if (response.ok) {
                const data = await response.json();

                if (data.success) {
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
                } else {
                    throw new Error(data.error);
                }
            } else {
                throw new Error('Server error');
            }
        });
    },

    updateSnapshot(project: TimelapseProject, snapshot: TimelapseSnapshot) {
        // snapshot.pages = snapshot.pages.sort();
        // const index = project.snapshots.findIndex(s => s.commit_sha === snapshot.commit_sha);
        // const nextProject: TimelapseProject = {
        //     ...project,
        //     snapshots: [
        //         ...project.snapshots.slice(0, index),
        //         snapshot as TimelapseSnapshot,
        //         ...project.snapshots.slice(index + 1)
        //     ]
        // };
        // this.project.next(nextProject);

        // // update current snapshot if it's the same (since it might have changed)
        // if (this.currentSnapshot.value?.commit_sha === snapshot.commit_sha) {
        //     this.currentSnapshot.next(snapshot as TimelapseSnapshot);
        // }
    },

    async resetSnapshot(commit_sha: string, stage?: number) {
        const project = this.project.value;
        if (!project) return false;

        const request = await fetch(`/api/projects/${project.name}/snapshot/${commit_sha}/reset/${stage}`);
        try {
            const response = await request.json();
            if (response.success) {
                this.updateSnapshot(project, response.snapshot as TimelapseSnapshot);
            } else {
                console.error(response.error);
            }

            return response.success as boolean;
        } catch (e) {
            console.error(e);
            return false;
        }
    }
};

const socket = io();
const snapshotUpdates = new Subject<TimelapseSnapshot>();
export const snapshotUpdates$ = snapshotUpdates.asObservable();

socket.on('stage', ({ stage, length }: { stage: string, length: number }) => {
    // TODO
    console.log('stage', stage, length);
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

socket.on('set_progress', ({ set }: { set: number }) => {
    // TODO
    console.log('set_progress', set);
});

socket.on('log', ({ msg, snapshot }: { msg: string, snapshot?: string }) => {
    // TODO
    console.log('log', msg, snapshot);
});

