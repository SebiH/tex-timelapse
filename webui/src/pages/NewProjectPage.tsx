import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { FolderArchive } from 'lucide-react';
import {
    Tabs,
    TabsContent,
    TabsList,
    TabsTrigger,
} from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { useState } from 'react';

export const NewProjectPage = () => {
    const [ projectName, setProjectName ] = useState('');

    return (
        <div className="mx-auto flex w-full h-full flex-col justify-center center-items space-y-6 sm:w-[550px]">
            <h1 className="text-3xl font-bold">Import a LaTeX project</h1>

            <Tabs defaultValue='zip' className="w-[400px]">
                <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="zip">
                        <FolderArchive className='mr-2 w-4 h-4' />
                        Zip file
                    </TabsTrigger>
                    <TabsTrigger value="overleaf">Overleaf (coming soon?)</TabsTrigger>
                </TabsList>
                <TabsContent value="zip">
                    <Card>
                        <CardHeader>
                            <CardTitle>Import Zip File</CardTitle>
                            <CardDescription>
                                Drag and drop a zip file containing your LaTeX project here.
                                The project should be at the root of the zip file.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="space-y-1">
                                <Label htmlFor="name">Project Name</Label>
                                <Input id="name" placeholder="My Research Paper" value={projectName} value={setProjectName.bind(this)} />
                            </div>
                        
                            <div className="space-y-1">
                                <Separator className="my-4" />
                            </div>
                        
                            <div className='dropzone'>
                                <Input type='file' />
                                <p className='text-muted-foreground text-sm'>
                                    Drag and drop your zip file here
                                </p>
                            </div>

                        </CardContent>
                        <CardFooter>
                            <Button>Start import</Button>
                        </CardFooter>
                    </Card>
                </TabsContent>
                <TabsContent value="overleaf">
                    <Card>
                        <CardHeader>
                            <CardTitle>Overleaf Import</CardTitle>
                            <CardDescription>
                                Import projects from Overleaf. <i>Due to API rate limits, this can take a few days!</i>
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <div className="space-y-1">
                                <Label htmlFor="account">Account Email</Label>
                                <Input id="account" type="email" />
                            </div>
                            <div className="space-y-1">
                                <Label htmlFor="password">password</Label>
                                <Input id="password" type="password" />
                            </div>
                        </CardContent>
                        <CardFooter>
                            <Button>Start Import</Button>
                        </CardFooter>
                    </Card>
                </TabsContent>
            </Tabs>


        </div>
    );

};
