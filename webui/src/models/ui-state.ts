import { TimelapseProject } from './project';
import { BehaviorSubject } from 'rxjs';
import { TimelapseSnapshot } from './snapshot';

export const UIState = {
    project: new BehaviorSubject<TimelapseProject | null>(null),
    currentSnapshot: new BehaviorSubject<TimelapseSnapshot | null>(null),

    setProject(project: TimelapseProject) {
        if (project !== this.project.value) {
            this.project.next(project);
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
                const index = project.snapshots.findIndex(s => s.commit_sha === commit_sha);
                const nextProject: TimelapseProject = {
                    ...project,
                    snapshots: [
                        ...project.snapshots.slice(0, index),
                        response.snapshot as TimelapseSnapshot,
                        ...project.snapshots.slice(index + 1)
                    ]
                };
                this.project.next(nextProject);

                // update current snapshot if it's the same (since it might have changed)
                if (this.currentSnapshot.value?.commit_sha === commit_sha) {
                    this.currentSnapshot.next(response.snapshot as TimelapseSnapshot);
                }
            }

            return response.success as boolean;
        } catch (e) {
            console.error(e);
            return false;
        }
    }
};

