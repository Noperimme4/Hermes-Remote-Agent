"""
Remote File Server - Handles virtual file system requests from Hermes/server side.
Forwards file operations to connected clients over the Agent channel.
"""

import asyncio
import base64
import os
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Awaitable, Any, List
from pathlib import Path

from shared.protocol import (
    BaseMessage,
    MessageType,
    RemoteFileOpenRequest,
    RemoteFileOpenResponse,
    RemoteFileReadRequest,
    RemoteFileWriteRequest,
    RemoteFileSeekRequest,
    RemoteFileCloseRequest,
    RemoteFileStatRequest,
    RemoteFileStatResponse,
    RemoteFileListRequest,
    RemoteFileListResponse,
    RemoteFileChunk,
    RemoteFileError,
    FileInfo,
    parse_message,
)

logger = logging.getLogger(__name__)


@dataclass
class RemoteFileHandle:
    """Represents an open file handle on a client."""
    handle_id: str
    client_id: str  # which client has this file open
    path: str
    mode: str
    size: int
    position: int = 0
    is_dir: bool = False


class RemoteFileServer:
    """
    Server-side virtual file system manager.
    
    When Hermes (or any server-side code) opens 'file://remote/path/to/file',
    the server:
    1. Determines which client owns that path (via mount points)
    2. Sends REMOTE_FILE_OPEN to that client
    3. Tracks the handle
    4. Subsequent read/seek/close go to the same client
    """
    
    def __init__(self, send_callback: Callable[[str], Awaitable[None]]):
        """
        Args:
            send_callback: Async function to send message to client (json string)
        """
        self.send_callback = send_callback
        self.handles: Dict[str, RemoteFileHandle] = {}  # handle_id -> handle
        self.client_mounts: Dict[str, Dict[str, str]] = {}  # client_id -> {mount_point: local_path}
        self.default_client: Optional[str] = None
        self._pending: Dict[str, asyncio.Future] = {}  # request_id -> future
        self._lock = asyncio.Lock()
    
    def register_client(self, client_id: str, mounts: Dict[str, str] = None):
        """Register a client with its mount points.
        
        Args:
            client_id: Unique client identifier
            mounts: Dict of {mount_point: local_path} e.g. {"/remote": "/home/user"}
        """
        self.client_mounts[client_id] = mounts or {"/": "/"}
        if self.default_client is None:
            self.default_client = client_id
        logger.info(f"Registered client {client_id} with mounts: {self.client_mounts[client_id]}")
    
    def unregister_client(self, client_id: str):
        """Unregister a client and clean up its handles."""
        if client_id in self.client_mounts:
            del self.client_mounts[client_id]
        # Close all handles belonging to this client
        handles_to_close = [h for h in self.handles.values() if h.client_id == client_id]
        for handle in handles_to_close:
            del self.handles[handle.handle_id]
        if self.default_client == client_id:
            self.default_client = next(iter(self.client_mounts.keys()), None)
        logger.info(f"Unregistered client {client_id}")
    
    def _resolve_path(self, path: str) -> tuple[Optional[str], Optional[str], str]:
        """
        Resolve a remote path to (client_id, local_path, mount_point).
        
        Returns: (client_id, local_path, mount_point) or (None, None, error_msg)
        """
        path = os.path.normpath(path)
        
        best_match = None
        best_client = None
        
        for client_id, mounts in self.client_mounts.items():
            for mount_point, local_base in mounts.items():
                if path == mount_point or path.startswith(mount_point.rstrip('/') + '/'):
                    if best_match is None or len(mount_point) > len(best_match):
                        best_match = mount_point
                        best_client = client_id
        
        if best_client is None:
            if self.default_client:
                return self.default_client, path, "/"
            return None, None, "No client available for remote file access"
        
        mount = self.client_mounts[best_client][best_match]
        if path == best_match:
            local_path = mount
        else:
            rel = path[len(best_match):].lstrip('/')
            local_path = os.path.join(mount, rel)
        
        return best_client, local_path, best_match
    
    async def handle_message(self, message: BaseMessage) -> Optional[BaseMessage]:
        """Handle incoming remote file message from client."""
        if isinstance(message, RemoteFileChunk):
            return await self._handle_chunk(message)
        elif isinstance(message, RemoteFileError):
            return await self._handle_error(message)
        elif isinstance(message, RemoteFileStatResponse):
            return await self._handle_stat_response(message)
        elif isinstance(message, RemoteFileListResponse):
            return await self._handle_list_response(message)
        elif isinstance(message, RemoteFileOpenResponse):
            return await self._handle_open_response(message)
        return None
    
    async def _handle_chunk(self, chunk: RemoteFileChunk):
        """Handle incoming file chunk from client (response to read)."""
        future = self._pending.get(chunk.request_id)
        if future and not future.done():
            future.set_result(chunk)
        else:
            logger.warning(f"No pending request for chunk {chunk.request_id}")
    
    async def _handle_error(self, error: RemoteFileError):
        """Handle error response from client."""
        future = self._pending.get(error.request_id)
        if future and not future.done():
            future.set_exception(Exception(f"{error.code}: {error.message}"))
        else:
            logger.warning(f"No pending request for error {error.request_id}")
    
    async def _handle_stat_response(self, resp: RemoteFileStatResponse):
        """Handle stat response from client."""
        future = self._pending.get(resp.request_id)
        if future and not future.done():
            future.set_result(resp)
        else:
            logger.warning(f"No pending request for stat response {resp.request_id}")
    
    async def _handle_list_response(self, resp: RemoteFileListResponse):
        """Handle list response from client."""
        future = self._pending.get(resp.request_id)
        if future and not future.done():
            future.set_result(resp)
        else:
            logger.warning(f"No pending request for list response {resp.request_id}")
    
    async def _handle_open_response(self, resp: RemoteFileOpenResponse):
        """Handle open response from client."""
        future = self._pending.get(resp.request_id)
        if future and not future.done():
            future.set_result(resp)
        else:
            logger.warning(f"No pending request for open response {resp.request_id}")
    
    def resolve_future(self, request_id: str, response: BaseMessage):
        """Resolve a pending future with response (called by message router)."""
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(response)
    
    # ─── High-level API for server-side code (Hermes) ─────────────────
    
    async def open(self, path: str, mode: str = "rb") -> RemoteFileOpenResponse:
        """Open a remote file (called by Hermes/server-side code)."""
        client_id, local_path, mount = self._resolve_path(path)
        
        if client_id is None:
            return RemoteFileOpenResponse(
                request_id=str(uuid.uuid4()),
                success=False,
                error="No client available for remote file access"
            )
        
        # Send open request to client
        req = RemoteFileOpenRequest(path=path, mode=mode)
        await self.send_callback(req.to_json())
        
        # Wait for response
        future = asyncio.Future()
        self._pending[req.request_id] = future
        try:
            response = await asyncio.wait_for(future, timeout=10)
        except asyncio.TimeoutError:
            return RemoteFileOpenResponse(
                request_id=req.request_id,
                success=False,
                error="Timeout waiting for client open response"
            )
        finally:
            self._pending.pop(req.request_id, None)
        
        if response.success:
            handle = RemoteFileHandle(
                handle_id=response.handle,
                client_id=client_id,
                path=path,
                mode=mode,
                size=response.size,
                is_dir=response.is_dir
            )
            self.handles[response.handle] = handle
        
        return response
    
    async def read(self, handle_id: str, offset: int, length: int) -> RemoteFileChunk:
        """Read chunk from remote file."""
        handle = self.handles.get(handle_id)
        if not handle:
            raise ValueError(f"Invalid handle: {handle_id}")
        
        req = RemoteFileReadRequest(handle=handle_id, offset=offset, length=length)
        await self.send_callback(req.to_json())
        
        future = asyncio.Future()
        self._pending[req.request_id] = future
        try:
            chunk = await asyncio.wait_for(future, timeout=30)
            return chunk
        finally:
            self._pending.pop(req.request_id, None)
    
    async def write(self, handle_id: str, offset: int, data: bytes) -> bool:
        """Write chunk to remote file."""
        handle = self.handles.get(handle_id)
        if not handle:
            raise ValueError(f"Invalid handle: {handle_id}")
        
        req = RemoteFileWriteRequest(
            handle=handle_id,
            offset=offset,
            data=base64.b64encode(data).decode()
        )
        await self.send_callback(req.to_json())
        
        future = asyncio.Future()
        self._pending[req.request_id] = future
        try:
            await asyncio.wait_for(future, timeout=30)
            return True
        finally:
            self._pending.pop(req.request_id, None)
    
    async def seek(self, handle_id: str, offset: int, whence: int = 0) -> int:
        """Seek in remote file."""
        handle = self.handles.get(handle_id)
        if not handle:
            raise ValueError(f"Invalid handle: {handle_id}")
        
        req = RemoteFileSeekRequest(handle=handle_id, offset=offset, whence=whence)
        await self.send_callback(req.to_json())
        
        future = asyncio.Future()
        self._pending[req.request_id] = future
        try:
            await asyncio.wait_for(future, timeout=10)
        finally:
            self._pending.pop(req.request_id, None)
        
        if whence == 0:
            handle.position = offset
        elif whence == 1:
            handle.position += offset
        elif whence == 2:
            handle.position = handle.size + offset
        
        return handle.position
    
    async def close(self, handle_id: str) -> bool:
        """Close remote file handle."""
        handle = self.handles.pop(handle_id, None)
        if not handle:
            return False
        
        req = RemoteFileCloseRequest(handle=handle_id)
        await self.send_callback(req.to_json())
        
        future = asyncio.Future()
        self._pending[req.request_id] = future
        try:
            await asyncio.wait_for(future, timeout=10)
        finally:
            self._pending.pop(req.request_id, None)
        
        return True
    
    async def stat(self, path: str) -> RemoteFileStatResponse:
        """Stat remote file (get metadata without opening)."""
        req = RemoteFileStatRequest(path=path)
        await self.send_callback(req.to_json())
        
        future = asyncio.Future()
        self._pending[req.request_id] = future
        try:
            return await asyncio.wait_for(future, timeout=10)
        finally:
            self._pending.pop(req.request_id, None)
    
    async def list(self, path: str) -> RemoteFileListResponse:
        """List remote directory."""
        req = RemoteFileListRequest(path=path)
        await self.send_callback(req.to_json())
        
        future = asyncio.Future()
        self._pending[req.request_id] = future
        try:
            return await asyncio.wait_for(future, timeout=10)
        finally:
            self._pending.pop(req.request_id, None)


class RemoteFile:
    """
    Synchronous file-like object for server-side code (Hermes) to access remote files.
    Runs async operations in the event loop.
    """
    
    def __init__(self, server: RemoteFileServer, path: str, mode: str = "rb"):
        self.server = server
        self.path = path
        self.mode = mode
        self.handle_id: Optional[str] = None
        self.position = 0
        self.closed = False
        self.size = 0
        self._loop = None
    
    def _get_loop(self):
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
        return self._loop
    
    def open(self):
        """Open the remote file."""
        loop = self._get_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._async_open(), loop)
            result = future.result(timeout=10)
        else:
            result = loop.run_until_complete(self._async_open())
        
        self.handle_id = result.handle
        self.size = result.size
        self.position = 0
        self.closed = False
    
    async def _async_open(self):
        req = RemoteFileOpenRequest(path=self.path, mode=self.mode)
        await self.server.send_callback(req.to_json())
        
        future = asyncio.Future()
        self.server._pending[req.request_id] = future
        response = await asyncio.wait_for(future, timeout=10)
        self.server._pending.pop(req.request_id, None)
        
        if not response.success:
            raise IOError(f"Failed to open remote file: {response.error}")
        
        return response
    
    def read(self, size: int = -1) -> bytes:
        """Read bytes from remote file."""
        if self.closed:
            raise ValueError("I/O operation on closed file")
        
        if size == -1:
            size = self.size - self.position
        
        if self.position + size > self.size:
            size = self.size - self.position
        
        if size <= 0:
            return b""
        
        loop = self._get_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._async_read(size), loop)
            data = future.result(timeout=30)
        else:
            data = loop.run_until_complete(self._async_read(size))
        
        self.position += len(data)
        return data
    
    async def _async_read(self, size: int) -> bytes:
        req = RemoteFileReadRequest(
            handle=self.handle_id,
            offset=self.position,
            length=size
        )
        await self.server.send_callback(req.to_json())
        
        future = asyncio.Future()
        self.server._pending[req.request_id] = future
        chunk = await asyncio.wait_for(future, timeout=30)
        self.server._pending.pop(req.request_id, None)
        
        if isinstance(chunk, RemoteFileError):
            raise IOError(f"Read error: {chunk.message}")
        
        import base64
        data = base64.b64decode(chunk.data)
        return data
    
    def seek(self, offset: int, whence: int = 0) -> int:
        """Seek in remote file."""
        loop = self._get_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._async_seek(offset, whence), loop)
            future.result(timeout=10)
        else:
            loop.run_until_complete(self._async_seek(offset, whence))
        return self.position
    
    async def _async_seek(self, offset: int, whence: int):
        req = RemoteFileSeekRequest(
            handle=self.handle_id,
            offset=offset,
            whence=whence
        )
        await self.server.send_callback(req.to_json())
        
        future = asyncio.Future()
        self.server._pending[req.request_id] = future
        await asyncio.wait_for(future, timeout=10)
        self.server._pending.pop(req.request_id, None)
        
        if whence == 0:
            self.position = offset
        elif whence == 1:
            self.position += offset
        elif whence == 2:
            self.position = self.size + offset
    
    def tell(self) -> int:
        return self.position
    
    def close(self):
        """Close the remote file."""
        if self.closed or not self.handle_id:
            return
        
        loop = self._get_loop()
        if loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._async_close(), loop)
            future.result(timeout=10)
        else:
            loop.run_until_complete(self._async_close())
        
        self.closed = True
        self.handle_id = None
    
    async def _async_close(self):
        req = RemoteFileCloseRequest(handle=self.handle_id)
        await self.server.send_callback(req.to_json())
        
        future = asyncio.Future()
        self.server._pending[req.request_id] = future
        await asyncio.wait_for(future, timeout=10)
        self.server._pending.pop(req.request_id, None)
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    def __iter__(self):
        return self
    
    def __next__(self):
        data = self.read(8192)
        if not data:
            raise StopIteration
        return data


class RemoteFileAsync:
    """Async version of RemoteFile for use in async code (Hermes)."""
    
    def __init__(self, server: RemoteFileServer, path: str, mode: str = "rb"):
        self.server = server
        self.path = path
        self.mode = mode
        self.handle_id: Optional[str] = None
        self.position = 0
        self.closed = False
        self.size = 0
    
    async def open(self):
        req = RemoteFileOpenRequest(path=self.path, mode=self.mode)
        await self.server.send_callback(req.to_json())
        
        future = asyncio.Future()
        self.server._pending[req.request_id] = future
        response = await asyncio.wait_for(future, timeout=10)
        self.server._pending.pop(req.request_id, None)
        
        if not response.success:
            raise IOError(f"Failed to open remote file: {response.error}")
        
        self.handle_id = response.handle
        self.size = response.size
        self.position = 0
        self.closed = False
        return self
    
    async def read(self, size: int = -1) -> bytes:
        if self.closed:
            raise ValueError("I/O operation on closed file")
        
        if size == -1:
            size = self.size - self.position
        
        if self.position + size > self.size:
            size = self.size - self.position
        
        if size <= 0:
            return b""
        
        req = RemoteFileReadRequest(
            handle=self.handle_id,
            offset=self.position,
            length=size
        )
        await self.server.send_callback(req.to_json())
        
        future = asyncio.Future()
        self.server._pending[req.request_id] = future
        chunk = await asyncio.wait_for(future, timeout=30)
        self.server._pending.pop(req.request_id, None)
        
        if isinstance(chunk, RemoteFileError):
            raise IOError(f"Read error: {chunk.message}")
        
        import base64
        data = base64.b64decode(chunk.data)
        self.position += len(data)
        return data
    
    async def seek(self, offset: int, whence: int = 0) -> int:
        req = RemoteFileSeekRequest(
            handle=self.handle_id,
            offset=offset,
            whence=whence
        )
        await self.server.send_callback(req.to_json())
        
        future = asyncio.Future()
        self.server._pending[req.request_id] = future
        await asyncio.wait_for(future, timeout=10)
        self.server._pending.pop(req.request_id, None)
        
        if whence == 0:
            self.position = offset
        elif whence == 1:
            self.position += offset
        elif whence == 2:
            self.position = self.size + offset
        
        return self.position
    
    def tell(self) -> int:
        return self.position
    
    async def close(self):
        if self.closed or not self.handle_id:
            return
        
        req = RemoteFileCloseRequest(handle=self.handle_id)
        await self.server.send_callback(req.to_json())
        
        future = asyncio.Future()
        self.server._pending[req.request_id] = future
        await asyncio.wait_for(future, timeout=10)
        self.server._pending.pop(req.request_id, None)
        
        self.closed = True
        self.handle_id = None
    
    async def __aenter__(self):
        await self.open()
        return self
    
    async def __aexit__(self, *args):
        await self.close()
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        data = await self.read(8192)
        if not data:
            raise StopAsyncIteration
        return data


async def remote_open(server: RemoteFileServer, path: str, mode: str = "rb") -> RemoteFileAsync:
    """Open a remote file asynchronously."""
    f = RemoteFileAsync(server, path, mode)
    await f.open()
    return f


async def remote_stat(server: RemoteFileServer, path: str) -> dict:
    """Stat a remote file."""
    req = RemoteFileStatRequest(path=path)
    await server.send_callback(req.to_json())
    
    future = asyncio.Future()
    server._pending[req.request_id] = future
    response = await asyncio.wait_for(future, timeout=10)
    server._pending.pop(req.request_id, None)
    
    if not response.success:
        raise IOError(f"Stat error: {response.error}")
    
    return {
        "size": response.size,
        "is_dir": response.is_dir,
        "modified": response.modified,
        "permissions": response.permissions
    }


async def remote_list(server: RemoteFileServer, path: str) -> list:
    """List remote directory."""
    req = RemoteFileListRequest(path=path)
    await server.send_callback(req.to_json())
    
    future = asyncio.Future()
    server._pending[req.request_id] = future
    response = await asyncio.wait_for(future, timeout=10)
    server._pending.pop(req.request_id, None)
    
    if not response.success:
        raise IOError(f"List error: {response.error}")
    
    return [
        {
            "name": e.name,
            "path": e.path,
            "size": e.size,
            "is_dir": e.is_dir,
            "modified": e.modified,
            "permissions": e.permissions
        }
        for e in response.entries
    ]