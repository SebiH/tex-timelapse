import { Badge } from '@/components/ui/badge';
import { TimelapseProject } from '@/models/project';

import './SnapshotView.scss';
import { SnapshotPages } from '@/features/snapshots/snapshot-pages';
import { SnapshotSlider } from '@/features/snapshots/snapshot-slider';
import { SnapshotInfo } from '@/features/snapshots/snapshot-info';
import { useEffect, useState } from 'react';
import { UIState } from '@/models/ui-state';
import { useToast } from '@/components/ui/use-toast';
import { socket } from '@/socketio';

export interface SnapshotViewProps {
    project: TimelapseProject
}

export const SnapshotView = (props: SnapshotViewProps) => {
    const [ snapshot, setSnapshot ] = useState(props.project.snapshots[0]);
    const { toast } = useToast();   

    useEffect(() => {
        socket.on('log', (data: any) => {
            console.log(data);
            toast({
                title: 'Log',
                description: JSON.stringify(data),
            });
        });
    }, []);

    useEffect(() => {
        const sub = UIState.currentSnapshot.subscribe(s => s && setSnapshot(s));
        return () => sub.unsubscribe();
    }, []);

    return <main className='grid flex-1 gap-4 overflow-none p-4 snapshot-view-grid'>

        <div className='relative hidden flex-col items-start gap-8 md:flex max-h-full overflow-y-auto'>
            <SnapshotInfo snapshot={snapshot} project={props.project} />
        </div>


        <div className='relative flex h-full min-h-[50vh] flex-col rounded-xl bg-muted/50 p-4 w-full overflow-y-auto max-h-full'>
            <SnapshotPages project={props.project} snapshot={snapshot} />

            <Badge variant='outline' className='absolute left-3 top-3 bg-white'>
                Snapshot Preview
            </Badge>
        </div>

        <div className='relative hidden flex-col items-start gap-8 md:flex col-span-2'>
            <SnapshotSlider snapshots={props.project.snapshots} onSelect={setSnapshot.bind(this)} />
        </div>

    </main>;
};
