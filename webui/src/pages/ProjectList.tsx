import { Link } from 'react-router-dom';

import './ProjectList.scss';
import { Button } from '@/components/ui/button';
import { CirclePlus, ExternalLink } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';

const ProjectList = () => {
    const { data, isLoading, isError, isSuccess } = useQuery({
        queryKey: ['projects'],
        queryFn: () => api.listProjects()
    });

    return (
        <div className='centered-container'>

            <div className="header">
                <h1 className='text-3xl font-bold'>TeX Timelapse</h1>
                <h2 className='text-2xl font-semibold'>Projects</h2>
            </div>

            <div className='project-list'>
                {isLoading && <div className='loading-indicator'></div>}
                {isError && <div className='error-message'>Failed to load projects.</div>}
                {isSuccess && data?.map((projectName) => (
                    <Link to={`/projects/${projectName}`} className='project-link' key={projectName}>
                        <div className='project-entry'>
                            {projectName}
                            <ExternalLink className='size-4' />
                        </div>

                    </Link>
                ))}

                <div className='centered-container'>
                    <Link to='/import'>
                        <Button className='flex flex-row gap-2'>
                            <CirclePlus />
                            Create New Project
                        </Button>
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default ProjectList;
