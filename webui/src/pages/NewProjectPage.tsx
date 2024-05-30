import { Button } from '@/components/ui/button';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from '@/components/ui/card';
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
  } from '@/components/ui/form';
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

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useToast } from '@/components/ui/use-toast';
import { useNavigate } from 'react-router-dom';
import { useState } from 'react';

const FormSchema = z.object({
    name: z.string().min(2, {
        message: 'Username must be at least 2 characters.',
    }),
    file: z.instanceof(FileList)
        .refine((file: FileList) => file, 'File is required')
        .refine((file: FileList) => file.length === 1 && file[0].name.endsWith('.zip') , 'Only one file in .zip format is supported.'),
});

export const NewProjectPage = () => {
    const navigate = useNavigate(); 
    const { toast } = useToast();
    const [ isUploading, setIsUploading ] = useState(false);

    const onSubmit = async (data: z.infer<typeof FormSchema>) => {
        setIsUploading(true);
        const formData = new FormData();
        formData.append('name', data.name);
        formData.append('file', data.file[0]);

        try {
            const response = await fetch('/api/import', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const result = await response.json();
            if (result.error) {
                throw new Error(result.error);
            }

            // navigate to new project page
            toast({ title: 'Project imported successfully' });
            navigate(`/projects/${result.name}`);

        } catch (error) {
            console.error('There was a problem with the fetch operation:', error);
            toast({ title: 'Failed to import project', variant: 'destructive' });
        }

        setIsUploading(false);
    };

    const form = useForm<z.infer<typeof FormSchema>>({
        resolver: zodResolver(FormSchema),
        defaultValues: {
            name: '',
            file: undefined
        },
    });
    const fileRef = form.register('file');

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
                                Import a zip file containing your LaTeX (git) project here.
                                The project should be at the root of the zip file.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-2">
                            <Form {...form}>
                                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
                                    <FormField
                                        control={form.control}
                                        name="name"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Project Name</FormLabel>
                                                <FormControl>
                                                    <Input placeholder="My Research Paper" {...field} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    <div className="space-y-1">
                                        <Separator className="my-4" />
                                    </div>

                                    <FormField
                                        control={form.control}
                                        name="file"
                                        render={({ field }) => (
                                            <FormItem>
                                                <FormLabel>Project File</FormLabel>
                                                <FormControl>
                                                    <Input type="file" accept='.zip' {...fileRef} />
                                                </FormControl>
                                                <FormMessage />
                                            </FormItem>
                                        )}
                                    />

                                    { !isUploading && <Button type="submit">Import</Button>}

                                    { isUploading && <Button disabled>
                                        <div className='loading-indicator w-4 h-4 mr-2'></div>
                                        Importing...
                                    </Button> }
                                </form>
                            </Form>
                        </CardContent>
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
                                <Label htmlFor="password">Password</Label>
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
