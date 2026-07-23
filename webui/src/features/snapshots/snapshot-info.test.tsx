import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { TimelapseProject } from '@/models/project';
import type { TimelapseSnapshot } from '@/models/snapshot';

// snapshot-info.tsx imports UIState, whose module opens a socket.io
// connection as a side effect of being imported - stub it out so rendering
// this component never touches the network.
vi.mock('socket.io-client', () => ({
    io: () => ({ on: vi.fn() }),
}));
vi.mock('@/api/client', () => ({
    api: {
        runSnapshot: vi.fn(),
        resetProject: vi.fn(),
        resetSnapshot: vi.fn(),
    },
}));

import { SnapshotInfo } from './snapshot-info';

function makeSnapshot(jobs: TimelapseSnapshot['jobs']): TimelapseSnapshot {
    return {
        commit_sha: 'abc123',
        commit_date: 0,
        main_tex_file: 'main.tex',
        status: 'Completed',
        error: '',
        includes: ['main.tex', 'chapters/intro.tex'],
        gitDiff: '',
        changed_pages: [],
        pages: [],
        jobs,
    };
}

const project: TimelapseProject = {
    name: 'demo',
    config: {} as TimelapseProject['config'],
    snapshots: [],
};

describe('SnapshotInfo', () => {
    it('derives one stage row per key in the jobs map, not a hardcoded list', () => {
        const snapshot = makeSnapshot({
            'Init Repo': 'Completed',
            'Replace Text': 'Completed',
            'Compile LaTeX': 'Failed',
            'A Brand New Stage': 'Unknown',
        });

        render(<SnapshotInfo project={project} snapshot={snapshot} />);

        for (const stage of Object.keys(snapshot.jobs)) {
            expect(screen.getByText(stage)).toBeInTheDocument();
        }
    });

    it('renders exactly as many stage rows as there are jobs, no more, no fewer', () => {
        const snapshot = makeSnapshot({
            'Init Repo': 'Completed',
            'Replace Text': 'Completed',
            'Compile LaTeX': 'In Progress',
        });

        const { container } = render(<SnapshotInfo project={project} snapshot={snapshot} />);

        expect(screen.getByText('Init Repo')).toBeInTheDocument();
        expect(container.querySelectorAll('.snapshot-job-status')).toHaveLength(3);
    });

    it('renders no stage rows when the jobs map is empty', () => {
        const snapshot = makeSnapshot({});

        const { container } = render(<SnapshotInfo project={project} snapshot={snapshot} />);

        expect(container.querySelectorAll('.snapshot-job-status')).toHaveLength(0);
    });
});
