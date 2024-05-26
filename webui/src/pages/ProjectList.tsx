import { Link, useLoaderData } from 'react-router-dom';

import './ProjectList.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlusCircle, faUpRightFromSquare } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@/components/ui/button';

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
                    {/* <Link to='/projects/new'> */}
                        <Button disabled>
                            <FontAwesomeIcon icon={faPlusCircle} className="mr-2 h-4 w-4" />
                            Create New Project (coming soon)
                        </Button>
                    {/* </Link> */}
                </div>
            </div>
        </div>
    );
};

export default ProjectList;