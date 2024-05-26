import './App.scss';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Root from './pages/Root';
import ProjectList, { loader as projectListLoader } from './pages/ProjectList';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import Project, { loader as projectLoader } from './pages/Project';
import { Toaster } from './components/ui/toaster';

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
        <div className="App bg-muted/40">
            <TooltipProvider>
                <RouterProvider router={router} />
            </TooltipProvider>
            <Toaster />
        </div>
    );
};

export default App;