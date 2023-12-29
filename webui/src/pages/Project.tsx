import { useLoaderData } from 'react-router-dom';

export async function loader({ params }: any) {
    return await fetch(`/api/projects/${params.projectName}`);
}

export default function Project() {
    const project = useLoaderData() as any;

    return (
        <div id='contact'>
            Hello, world!
            { JSON.stringify(project) }
        </div>
    );
}
