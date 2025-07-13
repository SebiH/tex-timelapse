import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Home, } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Link, LoaderFunctionArgs, useLoaderData } from 'react-router-dom';
import { TimelapseProject } from '@/models/project';
import { useEffect, useState } from 'react';
import { TimelapseView } from './TimelapseView';
import { VideoView } from './VideoView';
import { SnapshotView } from './SnapshotView';
import { UIState } from '@/models/ui-state';


export async function loader({ params }: LoaderFunctionArgs<{ projectName: string }>) {
    const query = await fetch(`/api/projects/${params.projectName}`);
    if (!query.ok) {
        throw new Response('Project not found', { status: 404 });
    }

    const result = await query.json();
    if (!result.project || result.success !== true) {
        throw new Response('Error loading project', { status: 404 });
    }

    return result.project as TimelapseProject;
}

const Project = () => {
    const [ project, setProject ] = useState<TimelapseProject>(useLoaderData() as TimelapseProject);
    const [view, setView] = useState('timelapse');

    useEffect(() => {
        UIState.setProject(project);
        const sub = UIState.project.subscribe(p => p && setProject(p));

        return () => sub.unsubscribe();
    }, []);


    let currentView = <TimelapseView project={project} />;
    if (view === 'snapshots') {
        currentView = <SnapshotView project={project} />;
    } else if (view === 'videos') {
        currentView = <VideoView project={project} />;
    }


    return (
        <div className='h-screen w-full'>

            <div className='flex flex-col h-full'>
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
