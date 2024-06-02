import { TimelapseProject } from '@/models/project';
import { TimelapseSnapshot } from '@/models/snapshot';
import {
    Alert,
    AlertDescription,
    AlertTitle,
} from '@/components/ui/alert';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import { Slider } from '@/components/ui/slider';
import { AlertCircle, Settings } from 'lucide-react';
import './snapshot-pages.scss';
import { Button } from '@/components/ui/button';
import { useState } from 'react';

export interface SnapshotPagesProps {
    project: TimelapseProject,
    snapshot: TimelapseSnapshot,
    blur?: number
}

export const SnapshotPages = (props: SnapshotPagesProps) => {
    const [ pageWidth, setPageWidth ] = useState([400]);

    const status = props.snapshot.status;
    if (status && status['PDF to Image'] === 'Completed') {

        const images = props.snapshot.pages.map((page, index) => {
            const pageChanged = !!props.snapshot.changed_pages.find(p => p.page === index + 1);
            const detailChanges = props.snapshot.changed_pages
                .filter(p => p.page === index + 1)
                .map(p => (
                    <div key={p.page} className='snapshot-page-detail-changes' style={{
                        'top': `${p.y1 * pageWidth[0]}px`,
                        'left': `${p.x1 * pageWidth[0]}px`,
                        'width': `${(p.x2 - p.x1) * pageWidth[0]}px`,
                        'height': `${(p.y2 - p.y1) * pageWidth[0]}px`
                    }}></div>
                ));

            return (
                <div className='snapshot-page-preview' key={page} style={{ 'width': `${pageWidth}px` }}>
                    {pageChanged && <div className='snapshot-page-changed' />}
                    {detailChanges}

                    <img src={`/api/projects/${props.project.name}/snapshot/${props.snapshot.commit_sha}/image/${page}`}
                        className='max-w-full'
                        style={{ 'filter': `blur(${props.blur}px)` }}
                        alt={`Page ${index}`}
                    />
                </div>
            );
        }
        );

        return <div className='w-full h-full relative overflow-y-auto'>
            <div className='w-full snapshot-pages-container'>
                {images}
            </div>

            <Popover>
                <PopoverTrigger asChild>
                    <Button variant="outline" className='absolute right-2 top-2'>
                        <Settings />
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-80">
                    <div className="grid gap-4">
                        <div className="space-y-2">
                            <h4 className="font-medium leading-none">Preview Page Size</h4>
                        </div>
                        <div className="grid gap-2">
                            <Slider step={1} value={pageWidth} min={50} max={1000} onValueChange={setPageWidth.bind(this)} />
                            <p className="text-sm text-muted-foreground">
                                Set the dimensions for the layer.
                            </p>
                        </div>
                    </div>
                </PopoverContent>
            </Popover>

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
