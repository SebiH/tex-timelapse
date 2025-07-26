import './TimelapseView.scss';
import { TimelapseProject } from '@/models/project';
import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { SnapshotPages } from '@/features/snapshots/snapshot-pages';
import { TimelapseSettings } from '@/features/timelapse/timelapse-settings';
import { HistogramSlider } from '@/features/histogram/histogram-slider';

export interface TimelapseViewProps {
    project: TimelapseProject
}

export const TimelapseView = (props: TimelapseViewProps) => {
    const [ isRendering, setIsRendering ] = useState(false);

    const [ startSnapshot, setStartSnapshot ] = useState(props.project.snapshots[0]);
    const [ endSnapshot, setEndSnapshot ] = useState(props.project.snapshots[props.project.snapshots.length - 1]);
    const [ snapshots, setSnapshots ] = useState(props.project.snapshots);

    return <main className='grid flex-1 gap-4 overflow-none p-4 project-view-grid'>

        <div className='relative hidden flex-col items-start gap-8 md:flex max-h-full overflow-y-auto project-view-config'>
            <TimelapseSettings project={props.project} />
        </div>


        <div className='relative flex h-full min-h-[50vh] flex-col rounded-xl bg-muted/50 p-4 w-full h-full project-view-main'>
            {isRendering && <div className='rendering-overlay'>
                <div className='flex flex-col items-center justify-center gap-4'>
                    <div className='loading-indicator'></div>
                    <p className='text-white'>Loading ...</p>
                </div>
            </div>}

            <SnapshotPages project={props.project} snapshot={startSnapshot} blur={props.project.config.blur} />

            <Badge variant='outline' className='absolute left-3 top-3 bg-white'>
                Preview
            </Badge>
        </div>

        <div className='relative hidden flex-col items-start gap-8 md:flex project-view-slider'>
            <HistogramSlider snapshots={snapshots} mode='single' startSnapshot={startSnapshot} endSnapshot={endSnapshot} />
        </div>

    </main>;
};
