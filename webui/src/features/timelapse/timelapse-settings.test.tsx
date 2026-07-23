import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { TimelapseProject } from '@/models/project';
import type { TimelapseConfig } from '@/models/config';

vi.mock('socket.io-client', () => ({
    io: () => ({ on: vi.fn() }),
}));
vi.mock('@/api/client', () => ({
    api: {
        runSnapshot: vi.fn(),
        resetProject: vi.fn(),
        resetSnapshot: vi.fn(),
        updateProjectConfig: vi.fn().mockResolvedValue(undefined),
        runProject: vi.fn(),
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
        useMultithreading: true,
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
});
