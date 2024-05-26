import { TimelapseProject } from '@/models/project';

export interface VideoViewProps {
    project: TimelapseProject
}

export const VideoView = (props: VideoViewProps) => {
    return <div>
        <h1>VideoView: { props.project.name }</h1>
    </div>;

};