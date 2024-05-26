import { TimelapseProject } from '@/models/project';
import { TimelapseSnapshot } from '@/models/snapshot';
import {
    Alert,
    AlertDescription,
    AlertTitle,
} from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import './snapshot-pages.scss';

export interface SnapshotPagesProps {
    project: TimelapseProject,
    snapshot: TimelapseSnapshot
}

export const SnapshotPages = (props: SnapshotPagesProps) => {
    const status = props.snapshot.status;
    if (status && status['PDF to Image'] === 'Completed') {

        const images = props.snapshot.pages.map((page, index) => {
            const pageChanged = (props.snapshot.changed_pages.includes(index + 1));

            return (
                <div className='snapshot-page-preview' key={page}>
                    {pageChanged && <div className='snapshot-page-changed' />}                   

                    <img src={`/api/projects/${props.project.name}/snapshot/${props.snapshot.commit_sha}/image/${page}`}
                        className='max-w-full'
                        alt={`Page ${index}`}
                    />
                </div>
            );
        }
        );

        return <div className='w-full relative overflow-y-auto'>
            <div className='w-full snapshot-pages-container'>
                {images}
            </div>
        </div>;

    } else {
        return <div className='w-full h-full relative flex items-center'>
            <Alert variant="default">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Snaphot not rendered</AlertTitle>
                <AlertDescription>
                    Render snapshot for preview.
                </AlertDescription>
            </Alert>
        </div>;
    }
};
