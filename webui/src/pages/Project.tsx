import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Home, } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Link, LoaderFunctionArgs, useLoaderData } from 'react-router-dom';
import { TimelapseProject } from '@/models/project';
import { useState } from 'react';
import { TimelapseView } from './TimelapseView';
import { VideoView } from './VideoView';
import { SnapshotView } from './SnapshotView';


export async function loader({ params }: LoaderFunctionArgs<{ projectName: string }>) {
    return await fetch(`/api/projects/${params.projectName}`);
}


const Project = () => {
    const project = useLoaderData() as TimelapseProject;
    const [view, setView] = useState('timelapse');

    let currentView = <TimelapseView project={project} />;
    if (view === 'snapshots') {
        currentView = <SnapshotView project={project} />;
    } else if (view === 'videos') {
        currentView = <VideoView project={project} />;
    }


    return (
        <div className='grid h-screen w-full'>

            <div className='flex flex-col'>
                <header className='sticky top-0 z-10 flex flex-row justify-between h-[57px] items-center gap-1 border-b bg-background'>
                    <div className='flex flex-row items-center'>
                        <div className='border-b p-2'>
                            <Link to='/'>
                                <Button variant='outline' size='icon' aria-label='Home'>
                                    <Home className='size-5' />
                                </Button>
                            </Link>
                        </div>

                        <h1 className='text-xl font-semibold'>
                            Tex Timelapse Project: { project.name }
                        </h1>

                    </div>

                    <Tabs defaultValue='timelapse' className='p-2' value={view} onValueChange={setView.bind(this)}>
                        <TabsList>
                            <TabsTrigger value='timelapse'>Timelapse</TabsTrigger>
                            <TabsTrigger value='snapshots'>Snapshots</TabsTrigger>
                            <TabsTrigger value='videos'>Videos</TabsTrigger>
                        </TabsList>
                    </Tabs>

                </header>
            
                {currentView}
            </div>
        </div>
    );
};

export default Project;
