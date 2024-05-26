import { Badge } from '@/components/ui/badge';
import { TimelapseProject } from '@/models/project';

import './SnapshotView.scss';
import { SnapshotPages } from '@/features/snapshots/snapshot-pages';
import { SnapshotSlider } from '@/features/snapshots/snapshot-slider';
import { SnapshotInfo } from '@/features/snapshots/snapshot-info';
import { useState } from 'react';

export interface SnapshotViewProps {
    project: TimelapseProject
}

export const SnapshotView = (props: SnapshotViewProps) => {
    const [ snapshot, setSnapshot ] = useState(props.project.snapshots[0]);

    return <main className='grid flex-1 gap-4 overflow-auto p-4 snapshot-view-grid'>

        <div className='relative hidden flex-col items-start gap-8 md:flex'>
            <SnapshotInfo snapshot={snapshot} project={props.project} />
        </div>


        <div className='relative flex h-full min-h-[50vh] flex-col rounded-xl bg-muted/50 p-4 w-full'>

            <Badge variant='outline' className='absolute right-3 top-3'>
                Snapshot Preview
            </Badge>

            <SnapshotPages />
        </div>

        <div className='relative hidden flex-col items-start gap-8 md:flex col-span-2'>
            <SnapshotSlider snapshots={props.project.snapshots} onSelect={setSnapshot.bind(this)} />
        </div>

    </main>;
};
