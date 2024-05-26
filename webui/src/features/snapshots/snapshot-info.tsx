import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { BugPlay } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { TimelapseSnapshot } from '@/models/snapshot';
import { TimelapseProject } from '@/models/project';

export interface SnapshotInfoProps {
    project: TimelapseProject,
    snapshot: TimelapseSnapshot
}

export const SnapshotInfo = (props: SnapshotInfoProps) => {
    const { toast } = useToast();

    const compileSnapshot = async () => {
        const commit_sha = props.snapshot.commit_sha;
        const request = await fetch(`/api/projects/${props.project.name}/snapshot/${commit_sha}/run`);
        const response = await request.json();

        // TODO: show toast with response
        if (response.success) {
            toast({
                title: 'Success!',
                description: 'Snapshot compiled successfully',
                // action: <ToastAction altText="View">Go to snapshot</ToastAction>,
            });
        } else {
            toast({
                title: 'Error',
                description: 'Snapshot could not be compiled',
                // action: <ToastAction altText="View">Go to snapshot</ToastAction>,
            });
        }
    };

    return <div className='flex flex-col justify-between w-full h-full'>

        <form className='grid w-full items-start gap-6 overflow-y-auto'>

            <fieldset className='grid gap-6 rounded-lg border p-4'>
                <legend className='-ml-1 px-1 text-sm font-medium'>
                    Snapshot Info
                </legend>

                <div className='grid gap-3'>
                    <Label htmlFor='temperature'>Date</Label>
                    <Input disabled value={new Date(props.snapshot.commit_date * 1000).toUTCString()} />

                    <Label htmlFor='temperature'>SHA</Label>
                    <Input disabled value={props.snapshot.commit_sha} />

                    <Label htmlFor='temperature'>Status</Label>
                    <pre><code>{ JSON.stringify(props.snapshot.status, null, 2) }</code></pre>

                    <Label htmlFor='temperature'>Includes</Label>
                    <pre><code>{ JSON.stringify(props.snapshot.includes, null, 2) }</code></pre>
                </div>
            </fieldset>

            {props.snapshot.error &&
                <fieldset className='grid gap-6 rounded-lg border p-4'>
                    <legend className='-ml-1 px-1 text-sm font-medium'>
                        Error
                    </legend>
                </fieldset>
            }

        </form>

        <Button variant='default' className='w-full' onClick={compileSnapshot.bind(this)}>
            <BugPlay className='w-4 h-4 m-1' />

            Render Snapshot
        </Button>

    </div>;
};
