import { Badge } from '@/components/ui/badge';
import { TimelapseProject } from '@/models/project';

import './SnapshotView.scss';
import { SnapshotPages } from '@/features/snapshots/snapshot-pages';
import { SnapshotSlider } from '@/features/snapshots/snapshot-slider';
import { SnapshotInfo } from '@/features/snapshots/snapshot-info';
import { useEffect, useState } from 'react';
import { UIState } from '@/models/ui-state';

export interface SnapshotViewProps {
    project: TimelapseProject
}

export const SnapshotView = (props: SnapshotViewProps) => {
    const [ snapshot, setSnapshot ] = useState(props.project.snapshots[0]);
    const [ snapshots, setSnapshots ] = useState(props.project.snapshots);

    useEffect(() => {
        const subs = [
            UIState.currentSnapshot.subscribe(s => s && setSnapshot(s)),
            UIState.project.subscribe(p => p && setSnapshots(p.snapshots))
        ];
        return () => subs.forEach(s => s.unsubscribe());
    }, []);

    // TODO: update this once we have a proper status
    const isRendering = () => {
        for (const key in snapshot?.status) {
            if (snapshot.status[key] === 'In Progress')
                return true;
        }

        return false;
    };

    return <main className='grid flex-1 gap-4 overflow-none p-4 snapshot-view-grid'>

        <div className='relative hidden flex-col items-start gap-8 md:flex max-h-full overflow-y-auto snapshot-view-config'>
            <SnapshotInfo snapshot={snapshot} project={props.project} />
        </div>


        <div className='relative flex h-full min-h-[50vh] flex-col rounded-xl bg-muted/50 p-4 w-full h-full snapshot-view-main'>
            {isRendering() && <div className='rendering-overlay'>
                <div className='flex flex-col items-center justify-center gap-4'>
                    <div className='loading-indicator'></div>
                    <p className='text-white'>Loading ...</p>
                </div>
            </div>}

            <SnapshotPages project={props.project} snapshot={snapshot} />

            <Badge variant='outline' className='absolute left-3 top-3 bg-white'>
                Snapshot Preview
            </Badge>
        </div>

        <div className='relative hidden flex-col items-start gap-8 md:flex snapshot-view-slider'>
            <SnapshotSlider snapshots={snapshots} mode='single' startSnapshot={snapshot} />
        </div>

    </main>;
};
