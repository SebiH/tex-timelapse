import { Link } from 'react-router-dom';

import './ProjectList.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faUpRightFromSquare } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@/components/ui/button';
import { CirclePlus } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

const ProjectList = () => {
    const { data, isLoading, isError, isSuccess } = useQuery({
        queryKey: ['projects'],
        queryFn: async () => {
            const data = await fetch('/api/projects');
            const response = await data.json();
            return response.projects as string[];
        }
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
                            <FontAwesomeIcon icon={faUpRightFromSquare} />
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
