import { Outlet, useNavigation } from 'react-router-dom';

export default function Root() {
    const navigation = useNavigation();

    return (
        <>
            <h1>Tex Timelapse</h1>
            <div className={ navigation.state === 'loading' ? 'loading' : '' } >
                <Outlet />
            </div>
        </>
    );
}