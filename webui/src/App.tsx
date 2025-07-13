import './App.scss';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import Root from './pages/Root';
import ProjectList from './pages/ProjectList';
import { TooltipProvider } from '@radix-ui/react-tooltip';
import Project, { loader as projectLoader } from './pages/Project';
import { Toaster } from './components/ui/sonner';
import { NewProjectPage } from './pages/NewProjectPage';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient();

const router = createBrowserRouter([
    {
        path: '/',
        element: <Root />,
        children: [
            {
                index: true,
                element: <ProjectList />,
            },

            {
                path: 'import/',
                element: <NewProjectPage />
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
            <QueryClientProvider client={queryClient}>
                <TooltipProvider>
                    <RouterProvider router={router} />
                </TooltipProvider>
                <Toaster />
            </QueryClientProvider>
        </div>
    );
};

export default App;