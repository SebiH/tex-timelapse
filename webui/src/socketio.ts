import { io } from 'socket.io-client';
export const socket = io();

socket.on('message', (data: any) => {
    console.log(data);
});
