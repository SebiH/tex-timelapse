import { Outlet, useNavigation } from 'react-router-dom';
import { ErrorBoundary, FallbackProps } from 'react-error-boundary';

import './Root.scss';

const fallbackRender = ({ error }: FallbackProps) => {
    return (
        <div role="alert">
            <p>Something went wrong:</p>
            <pre style={{ color: 'red' }}>{error.message}</pre>
        </div>
    );
};


export default function Root() {
    const navigation = useNavigation();

    return (
        <ErrorBoundary
            fallbackRender={fallbackRender}>
            <Outlet />

            {
                navigation.state === 'loading' &&
                <div className='overlay'>
                    <div className='loading-indicator'></div>
                </div>
            }
        </ErrorBoundary>
    );
}