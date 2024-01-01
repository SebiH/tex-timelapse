import { Link, useLoaderData } from 'react-router-dom';

import './ProjectList.scss';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlusCircle, faUpRightFromSquare } from '@fortawesome/free-solid-svg-icons';

export async function loader() {
    return await fetch('/api/projects');
}

const ProjectList = () => {
    const projectNames = useLoaderData() as string[] || [];

    return (
        <div className='centered-container'>

            <div className="header">
                <h1>TeX Timelapse</h1>
                <h2>Projects</h2>
            </div>

            <div className='projects'>
                {projectNames.map((projectName) => (
                    <Link to={`/projects/${projectName}`} className='project-link' key={projectName}>
                        <div className='project'>
                            {projectName}
                            <FontAwesomeIcon icon={faUpRightFromSquare} />
                        </div>

                    </Link>
                ))}

                <div className='centered-container'>
                    <Link to='/projects/new' className='main-btn'>
                        <div className='btn-icon'>
                            <FontAwesomeIcon icon={faPlusCircle} />
                        </div>

                        <div className='btn-content'>
                            Create New Project
                        </div>
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default ProjectList;