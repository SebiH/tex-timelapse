import { TimelapseSnapshot } from '@/models/snapshot';

// Shared by histogram.tsx (and, transitively, histogram-slider.tsx) so the
// bar geometry and status-colour mapping only exist in one place.

export const HISTOGRAM_HEIGHT = 20;

export function getSnapshotColor(snapshot: TimelapseSnapshot): string {
    switch (snapshot.status) {
        case 'In Progress':
            return '#EBCB8B';
        case 'Completed':
            return '#A3BE8C';
        case 'Failed':
            return '#BF616A';
        default:
            return '#D8DEE9';
    }
}

// Margin between bars, in px: thin enough not to eat into narrow bars when
// there are many snapshots, capped so it doesn't look silly when there are few.
export function getBarMargin(canvasWidth: number, snapshotCount: number): number {
    return Math.max(0, Math.min(5, Math.floor(canvasWidth / snapshotCount / 10)));
}

export function getBarWidth(canvasWidth: number, snapshotCount: number): number {
    return canvasWidth / snapshotCount;
}
