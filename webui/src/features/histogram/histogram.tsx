import './histogram.scss';
import { TimelapseSnapshot } from '../../models/snapshot';
import { useEffect, useRef } from 'react';
import { snapshotUpdates$, UIState } from '@/models/ui-state';
import { getBarMargin, getBarWidth, getSnapshotColor, HISTOGRAM_HEIGHT } from './histogram-utils';

type Props = {
    snapshots: TimelapseSnapshot[];
};

export const Histogram = ({ snapshots }: Props) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    // TODO: bucket the snapshots by day
    // const days = snapshots.map(s => Math.floor(s.commit_date / 1000 / 60 / 60 / 24))
    //     .sort((a, b) => a - b). filter((v, i, a) => a.indexOf(v) === i);

    // const min = snapshots.map(s => s.commit_date).reduce((a, b) => Math.min(a, b));
    // const max = snapshots.map(s => s.commit_date).reduce((a, b) => Math.max(a, b));
    // const getPosition = (time: number) => (time - min) / (max - min) * 100;

    useEffect(() => {
        const canvas = canvasRef.current;
        const container = containerRef.current;
        if (!canvas || !container) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const resizeCanvas = () => {
            const { width } = container.getBoundingClientRect();

            // Set canvas pixel dimensions (important!)
            canvas.width = width;
            canvas.height = HISTOGRAM_HEIGHT;

            // Clear and redraw
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const margin = getBarMargin(width, snapshots.length);
            const barWidth = getBarWidth(canvas.width, snapshots.length);
            snapshots.forEach((snapshot, index) => {
                ctx.fillStyle = getSnapshotColor(snapshot);
                ctx.fillRect(index * barWidth, canvas.height - HISTOGRAM_HEIGHT, barWidth - margin, HISTOGRAM_HEIGHT);
            });
        };

        resizeCanvas();

        const observer = new ResizeObserver(resizeCanvas);
        observer.observe(container);

        const snapshotUpdateHandler = snapshotUpdates$.subscribe((snapshot) => {
            const { width } = container.getBoundingClientRect();
            const margin = getBarMargin(width, snapshots.length);
            const barWidth = getBarWidth(canvas.width, snapshots.length);
            const index = snapshots.findIndex(s => s.commit_sha === snapshot.commit_sha);

            ctx.fillStyle = getSnapshotColor(snapshot);

            const concatCommits = UIState.project.value?.config?.concatCommits;
            if (!concatCommits) {
                ctx.fillRect(index * barWidth, canvas.height - HISTOGRAM_HEIGHT, barWidth - margin, HISTOGRAM_HEIGHT);
            } else {
                // find previous snapshot that was compiled
                const previousIndex = index - concatCommits;
                ctx.fillRect(previousIndex * barWidth, canvas.height - HISTOGRAM_HEIGHT, (index * barWidth) - (previousIndex * barWidth) - margin, HISTOGRAM_HEIGHT);
            }
        });

        return () => {
            observer.disconnect();
            snapshotUpdateHandler.unsubscribe();
        };
    }, [snapshots]);

    return (
        <div ref={containerRef} className="histogram-container">
            <canvas className="histogram" ref={canvasRef} />
        </div>
    );
};