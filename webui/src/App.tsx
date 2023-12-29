import './App.scss';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Root from './pages/Root';
import Project, { loader as projectLoader } from './pages/Project';
import ProjectList, { loader as projectListLoader } from './pages/ProjectList';

const router = createBrowserRouter([
    {
        path: '/',
        element: <Root />,
        children: [
            {
                index: true,
                element: <ProjectList />,
                loader: projectListLoader
            },

            {
                path: 'projects/:projectName',
                element: <Project />,
                loader: projectLoader
            }
        ]
    },
]);


const App = () => {
    return (
        <div className="App">
            <RouterProvider router={router} />
        </div>
    );
};

export default App;