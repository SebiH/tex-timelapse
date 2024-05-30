import { Link, useLoaderData } from 'react-router-dom';

import './ProjectList.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faUpRightFromSquare } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@/components/ui/button';
import { CirclePlus } from 'lucide-react';

export async function loader() {
    return await fetch('/api/projects');
}

const ProjectList = () => {
    const projectNames = useLoaderData() as string[] || [];

    return (
        <div className='centered-container'>

            <div className="header">
                <h1 className='text-3xl font-bold'>TeX Timelapse</h1>
                <h2 className='text-2xl font-semibold'>Projects</h2>
            </div>

            <div className='project-list'>
                {projectNames.map((projectName) => (
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
