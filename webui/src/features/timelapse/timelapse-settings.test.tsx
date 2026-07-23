import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import type { TimelapseProject } from '@/models/project';
import type { TimelapseConfig } from '@/models/config';
import type { TimelapseJob } from '@/models/job';

vi.mock('socket.io-client', () => ({
    io: () => ({ on: vi.fn() }),
}));
vi.mock('@/api/client', () => ({
    api: {
        runSnapshot: vi.fn(),
        resetProject: vi.fn(),
        resetSnapshot: vi.fn(),
        updateProjectConfig: vi.fn().mockResolvedValue(undefined),
        startRender: vi.fn(),
        cancelRender: vi.fn(),
    },
}));

import { TimelapseSettings } from './timelapse-settings';
import { UIState } from '@/models/ui-state';
import { api } from '@/api/client';

const lualatexCmd = 'latexmk -pdflatex=\'lualatex %O %S\' -interaction=nonstopmode -pdf -synctex=1 -f';
const pdflatexCmd = 'latexmk -pdf -interaction=nonstopmode -synctex=1 -f';

function makeConfig(overrides: Partial<TimelapseConfig> = {}): TimelapseConfig {
    return {
        rows: 3,
        columns: 4,
        videoscale: 1,
        framerate: 4,
        blur: 0,
        highlightChanges: true,
        workers: 1,
        startCommit: '',
        endCommit: '',
        crop: false,
        cropTwoPage: false,
        cropLeft: 0,
        cropRight: 0,
        cropTop: 0,
        cropBottom: 0,
        cropAltLeft: 0,
        cropAltRight: 0,
        cropAltTop: 0,
        cropAltBottom: 0,
        concatCommits: 0,
        text_replacements: [],
        latexCmd: pdflatexCmd,
        overleafProjectId: '',
        overleafAuthToken: '',
        ...overrides,
    };
}

function makeProject(config: TimelapseConfig): TimelapseProject {
    return {
        name: 'demo',
        config,
        snapshots: [],
    };
}

function makeJob(overrides: Partial<TimelapseJob> = {}): TimelapseJob {
    return {
        id: 'job1',
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

// The compiler <Select> mirrors `UIState.project`, not the `project` prop
// directly (see the subscription in timelapse-settings.tsx) - in the real
// app, the page component (src/pages/Project.tsx) always calls
// `UIState.setProject(...)` before this component's tree mounts, so priming
// the store here reproduces real usage rather than working around a bug.
function renderWithProject(project: TimelapseProject) {
    UIState.setProject(project);
    return render(<TimelapseSettings project={project} />);
}

describe('TimelapseSettings', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        UIState.project.next(null);
        UIState.currentSnapshot.next(null);
        UIState.activeJob.next(null);
    });

    it('reflects config.latexCmd in the compiler select (lualatex)', () => {
        const project = makeProject(makeConfig({ latexCmd: lualatexCmd }));
        renderWithProject(project);

        const hiddenSelect = document.querySelector('select[aria-hidden="true"]') as HTMLSelectElement | null;
        expect(hiddenSelect).not.toBeNull();
        expect(hiddenSelect!.value).toBe('lualatex');
    });

    it('reflects config.latexCmd in the compiler select (pdflatex default)', () => {
        const project = makeProject(makeConfig({ latexCmd: pdflatexCmd }));
        renderWithProject(project);

        const hiddenSelect = document.querySelector('select[aria-hidden="true"]') as HTMLSelectElement | null;
        expect(hiddenSelect).not.toBeNull();
        expect(hiddenSelect!.value).toBe('pdflatex');
    });

    it('falls back to custom when latexCmd matches none of the known presets', () => {
        const project = makeProject(makeConfig({ latexCmd: 'my-own-compiler-script.sh' }));
        renderWithProject(project);

        const hiddenSelect = document.querySelector('select[aria-hidden="true"]') as HTMLSelectElement | null;
        expect(hiddenSelect).not.toBeNull();
        expect(hiddenSelect!.value).toBe('custom');
        expect(screen.getByLabelText('Custom Compiler')).toHaveValue('my-own-compiler-script.sh');
    });

    it('clearing a numeric field does not push NaN into config (regression test for Part 1b)', () => {
        const project = makeProject(makeConfig({ rows: 3 }));
        render(<TimelapseSettings project={project} />);

        const rowsInput = screen.getAllByRole('spinbutton')[0] as HTMLInputElement;
        expect(rowsInput).toHaveValue(3);

        // Simulate the user clearing the field: jsdom computes valueAsNumber
        // as NaN for an empty number input, same as a real browser.
        fireEvent.change(rowsInput, { target: { value: '' } });

        // The guard must reject the NaN before it reaches config/UIState -
        // neither the store nor the (debounced) API call should ever see it.
        expect(UIState.project.value).toBeNull();
        expect(api.updateProjectConfig).not.toHaveBeenCalled();
    });

    it('updates config with a real number when a numeric field is edited to a valid value', () => {
        const project = makeProject(makeConfig({ rows: 3 }));
        render(<TimelapseSettings project={project} />);

        const rowsInput = screen.getAllByRole('spinbutton')[0] as HTMLInputElement;
        fireEvent.change(rowsInput, { target: { value: '7' } });

        expect(rowsInput).toHaveValue(7);
        expect(UIState.project.value?.config.rows).toBe(7);
    });

    describe('render controls', () => {
        it('starts a render with the project name as the output basename', async () => {
            const project = makeProject(makeConfig());
            vi.mocked(api.startRender).mockResolvedValue(makeJob());
            render(<TimelapseSettings project={project} />);

            fireEvent.click(screen.getByRole('button', { name: /start/i }));

            await waitFor(() => expect(api.startRender).toHaveBeenCalledWith('demo', 'demo'));
        });

        it('shows the current stage and progress, and swaps Start for Cancel, while a job is running', async () => {
            const project = makeProject(makeConfig());
            render(<TimelapseSettings project={project} />);

            UIState.activeJob.next(makeJob({ stage: 'Compile LaTeX', stage_progress: 0.5 }));

            expect(await screen.findByText('Compile LaTeX')).toBeInTheDocument();
            expect(screen.getByText('50%')).toBeInTheDocument();
            expect(screen.queryByRole('button', { name: /start/i })).not.toBeInTheDocument();
            expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
        });

        it('cancels the active job when Cancel is clicked', async () => {
            const project = makeProject(makeConfig());
            vi.mocked(api.cancelRender).mockResolvedValue(makeJob({ status: 'cancelled' }));
            render(<TimelapseSettings project={project} />);
            UIState.activeJob.next(makeJob({ stage: 'Compile LaTeX' }));

            fireEvent.click(await screen.findByRole('button', { name: /cancel/i }));

            await waitFor(() => expect(api.cancelRender).toHaveBeenCalledWith('job1'));
        });
    });
});
