import './histogram.scss';
import { TimelapseSnapshot } from '../../models/snapshot';
import { useEffect, useRef } from 'react';
import { snapshotUpdates$, UIState } from '@/models/ui-state';

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

        const getSnapshotColor = (s: TimelapseSnapshot) => {
            if (s.status === 'In Progress') {
                return '#EBCB8B';
            } else if (s.status === 'Completed') {
                return '#A3BE8C';
            } else if (s.status === 'Failed') {
                return '#BF616A';
            }
            return '#D8DEE9';
        };

        const height = 20;
        const resizeCanvas = () => {
            const { width } = container.getBoundingClientRect();

            // Set canvas pixel dimensions (important!)
            canvas.width = width;
            canvas.height = height;

            // Clear and redraw
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            const margin = Math.max(0, Math.min(5, Math.floor(width / snapshots.length / 10)));
            const barWidth = canvas.width / snapshots.length;
            snapshots.forEach((snapshot, index) => {
                ctx.fillStyle = getSnapshotColor(snapshot);
                ctx.fillRect(index * barWidth, canvas.height - height, barWidth - margin, height);
            });
        };

        resizeCanvas();

        const observer = new ResizeObserver(resizeCanvas);
        observer.observe(container);

        const snapshotUpdateHandler = snapshotUpdates$.subscribe((snapshot) => {
            const { width } = container.getBoundingClientRect();
            const margin = Math.max(0, Math.min(5, Math.floor(width / snapshots.length / 10)));
            
            if (!UIState.project.value?.config?.concatCommits) {
                const barWidth = canvas.width / snapshots.length;
                ctx.fillStyle = getSnapshotColor(snapshot);
                const index = snapshots.findIndex(s => s.commit_sha === snapshot.commit_sha);
                ctx.fillRect(index * barWidth, canvas.height - height, barWidth - margin, height);
            } else {
                ctx.fillStyle = getSnapshotColor(snapshot);
                const index = snapshots.findIndex(s => s.commit_sha === snapshot.commit_sha);
                // find previous snapshot that was compiled
                const previousIndex = index - UIState.project.value.config.concatCommits;
                const barWidth = canvas.width / snapshots.length;
                ctx.fillRect(previousIndex * barWidth, canvas.height - height, (index * barWidth) - (previousIndex * barWidth) - margin, height);
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