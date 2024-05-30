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

    useEffect(() => {
        const sub = UIState.currentSnapshot.subscribe(s => s && setSnapshot(s));
        return () => sub.unsubscribe();
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

        <div className='relative hidden flex-col items-start gap-8 md:flex max-h-full overflow-y-auto'>
            <SnapshotInfo snapshot={snapshot} project={props.project} />
        </div>


        <div className='relative flex h-full min-h-[50vh] flex-col rounded-xl bg-muted/50 p-4 w-full overflow-y-auto max-h-full'>
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

        <div className='relative hidden flex-col items-start gap-8 md:flex col-span-2'>
            <SnapshotSlider snapshots={props.project.snapshots} mode='single' startSnapshot={snapshot} />
        </div>

    </main>;
};
