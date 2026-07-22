import { TimelapseProject } from '@/models/project';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Construction } from 'lucide-react';

export interface VideoViewProps {
    project: TimelapseProject
}

// Not implemented: the server does not yet expose the rendered videos.
// `compileProject`/`__runProject` in `tex_timelapse/webserver.py` write to
// `projects/<slug>/output/*.mp4`, but there is no route serving that file
// (the `image/<basename>` route only serves `thumbnails/`). This view can
// start listing/playing videos once a route such as
// `GET /api/projects/<name>/output/<basename>` exists on the Python side.
export const VideoView = (props: VideoViewProps) => {
    return <div className='w-full h-full flex items-center justify-center p-4'>
        <Alert variant='default' className='max-w-md'>
            <Construction className='h-4 w-4' />
            <AlertTitle>Videos are not available yet</AlertTitle>
            <AlertDescription>
                The server does not currently expose the rendered video for
                &quot;{props.project.name}&quot;. This view will be able to list and play
                {' '}<code>output/*.mp4</code> once a backend endpoint for serving it exists.
            </AlertDescription>
        </Alert>
    </div>;
};