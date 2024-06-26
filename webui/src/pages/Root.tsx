import { Outlet, useNavigation } from 'react-router-dom';

import './Root.scss';

export default function Root() {
    const navigation = useNavigation();

    return (
        <>
            <Outlet />

            {
                navigation.state === 'loading' &&
                <div className='overlay'>
                    <div className='loading-indicator'></div>
                </div>
            }
        </>
    );
}