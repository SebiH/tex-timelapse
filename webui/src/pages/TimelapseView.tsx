import './TimelapseView.scss';
import { TimelapseProject } from '@/models/project';
import { Badge } from '@/components/ui/badge';
import { SnapshotPages } from '@/features/snapshots/snapshot-pages';
import { TimelapseSettings } from '@/features/timelapse/timelapse-settings';
import { Histogram } from '@/features/histogram/histogram';

export interface TimelapseViewProps {
    project: TimelapseProject
}

export const TimelapseView = (props: TimelapseViewProps) => {
    // Derived from props rather than held in state: the previous useState
    // copies never updated when the project changed, and their setters were
    // never called. A render-progress overlay belongs here once the API
    // exposes job status; SnapshotView shows the pattern, driven by real status.
    const startSnapshot = props.project.snapshots[0];
    const snapshots = props.project.snapshots;

    return <main className='grid flex-1 gap-4 overflow-none p-4 project-view-grid'>

        <div className='relative hidden flex-col items-start gap-8 md:flex max-h-full overflow-y-auto project-view-config'>
            <TimelapseSettings project={props.project} />
        </div>


        <div className='relative flex h-full min-h-[50vh] flex-col rounded-xl bg-muted/50 p-4 w-full h-full project-view-main'>
            <SnapshotPages project={props.project} snapshot={startSnapshot} blur={props.project.config.blur} />

            <Badge variant='outline' className='absolute left-3 top-3 bg-white'>
                Preview
            </Badge>
        </div>

        <div className='relative hidden flex-col items-start gap-8 md:flex project-view-slider'>
            <Histogram snapshots={snapshots} />
        </div>

    </main>;
};
