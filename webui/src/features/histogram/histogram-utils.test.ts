import { describe, it, expect } from 'vitest';
import { getSnapshotColor, getBarWidth, getBarMargin } from './histogram-utils';
import type { TimelapseSnapshot } from '@/models/snapshot';

function makeSnapshot(status: TimelapseSnapshot['status']): TimelapseSnapshot {
    return {
        commit_sha: 'abc',
        commit_date: 0,
        main_tex_file: 'main.tex',
        status,
        error: '',
        includes: [],
        gitDiff: '',
        changed_pages: [],
        pages: [],
        jobs: {},
    };
}

describe('getSnapshotColor', () => {
    it('maps every known status to its own color', () => {
        expect(getSnapshotColor(makeSnapshot('In Progress'))).toBe('#EBCB8B');
        expect(getSnapshotColor(makeSnapshot('Completed'))).toBe('#A3BE8C');
        expect(getSnapshotColor(makeSnapshot('Failed'))).toBe('#BF616A');
    });

    it('falls back to the neutral color for Unknown (and anything unrecognized)', () => {
        expect(getSnapshotColor(makeSnapshot('Unknown'))).toBe('#D8DEE9');
        expect(getSnapshotColor(makeSnapshot('something-else' as TimelapseSnapshot['status']))).toBe('#D8DEE9');
    });
});

describe('getBarWidth', () => {
    it('divides the canvas width evenly across snapshots', () => {
        expect(getBarWidth(400, 4)).toBe(100);
        expect(getBarWidth(400, 1)).toBe(400);
    });

    it('shrinks toward zero as the snapshot count grows large', () => {
        const width = getBarWidth(400, 1_000_000);
        expect(width).toBeGreaterThan(0);
        expect(width).toBeLessThan(0.001);
    });

    it('is Infinity for zero snapshots (division by zero)', () => {
        expect(getBarWidth(400, 0)).toBe(Infinity);
    });
});

describe('getBarMargin', () => {
    it('is capped at 5px when there is plenty of room per bar', () => {
        expect(getBarMargin(10_000, 1)).toBe(5);
    });

    it('floors to 0 once bars get small enough, however much room the canvas has', () => {
        expect(getBarMargin(400, 1_000_000)).toBe(0);
    });

    it('never goes negative for a single wide canvas and many snapshots', () => {
        const margin = getBarMargin(100, 1000);
        expect(margin).toBeGreaterThanOrEqual(0);
        expect(margin).toBeLessThanOrEqual(5);
    });

    it('clamps to the 5px cap for zero snapshots rather than NaN (division by zero -> Infinity, capped)', () => {
        expect(getBarMargin(400, 0)).toBe(5);
    });
});
