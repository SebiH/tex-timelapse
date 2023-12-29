import { Link, useLoaderData } from 'react-router-dom';

export async function loader() {
    return await fetch('/api/projects');
}

export default function ProjectList() {
    const projectNames = useLoaderData() as string[];

    return (
        <div>
            <ul>
                {projectNames.map((projectName) => (
                    <li key={projectName}>
                        <Link to={`/projects/${projectName}`}>
                            {projectName}
                        </Link>
                    </li>
                ))}
            </ul>
        </div>
    );
}
