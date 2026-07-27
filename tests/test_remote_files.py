"""
Integration tests for Remote File Access Protocol.
Tests virtual file system operations over the Agent channel.
"""

import asyncio
import base64
import os
import tempfile
import pytest
from pathlib import Path

# Add project to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.protocol import (
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

from server.remote_files import RemoteFileServer
from client.remote_files import RemoteFileProvider


class MockTransport:
    """Mock transport for testing message exchange."""
    
    def __init__(self):
        self.sent_messages = []
        self.received_messages = []
        self._server_queue = asyncio.Queue()
        self._client_queue = asyncio.Queue()
    
    async def server_send(self, message_json: str):
        """Server sends to client."""
        self.sent_messages.append(("server", message_json))
        await self._client_queue.put(message_json)
    
    async def client_send(self, message_json: str):
        """Client sends to server."""
        self.sent_messages.append(("client", message_json))
        await self._server_queue.put(message_json)
    
    async def server_receive(self) -> str:
        """Server receives from client."""
        msg = await self._server_queue.get()
        self.received_messages.append(("server", msg))
        return msg
    
    async def client_receive(self) -> str:
        """Client receives from server."""
        msg = await self._client_queue.get()
        self.received_messages.append(("client", msg))
        return msg


@pytest.fixture
def temp_dir():
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        
        # Create test structure
        (base / "file1.txt").write_text("Hello World\n" * 100)  # ~1.2KB
        (base / "file2.bin").write_bytes(os.urandom(10000))  # 10KB binary
        (base / "empty.txt").write_text("")
        (base / "large.dat").write_bytes(os.urandom(1024 * 1024))  # 1MB
        
        subdir = base / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("Nested content\n")
        (subdir / "deep").mkdir()
        (subdir / "deep" / "very_deep.txt").write_text("Deep!\n")
        
        yield base


@pytest.fixture
def transport():
    return MockTransport()


@pytest.fixture
async def server(transport, temp_dir):
    """Create RemoteFileServer with mock transport."""
    async def send_callback(msg_json):
        await transport.server_send(msg_json)
    
    server = RemoteFileServer(send_callback)
    server.register_client("test-client", {"/": str(temp_dir), "/home": str(temp_dir / "home")})
    yield server


@pytest.fixture
async def provider(transport, temp_dir):
    """Create RemoteFileProvider with mock transport."""
    async def send_callback(msg_json):
        await transport.client_send(msg_json)
    
    provider = RemoteFileProvider(send_callback, str(temp_dir))
    yield provider


class TestRemoteFileProtocol:
    """Test the remote file protocol message exchange."""
    
    @pytest.mark.asyncio
    async def test_open_read_close(self, server, provider, transport, temp_dir):
        """Test basic open -> read -> close cycle."""
        test_file = temp_dir / "file1.txt"
        test_content = test_file.read_bytes()
        
        # Server opens file
        open_req = RemoteFileOpenRequest(path="/file1.txt", mode="rb")
        await transport.server_send(open_req.to_json())
        
        # Provider receives and responds
        msg_json = await transport.client_receive()
        msg = parse_message(msg_json)
        assert isinstance(msg, RemoteFileOpenRequest)
        
        # Provider handles open
        await provider.handle_message(msg)
        
        # Get open response
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        assert isinstance(resp, RemoteFileOpenResponse)
        assert resp.success
        assert resp.size == len(test_content)
        assert not resp.is_dir
        handle = resp.handle
        
        # Server reads first chunk
        read_req = RemoteFileReadRequest(handle=handle, offset=0, length=100)
        await transport.server_send(read_req.to_json())
        
        # Provider handles read
        msg_json = await transport.client_receive()
        msg = parse_message(msg_json)
        assert isinstance(msg, RemoteFileReadRequest)
        await provider.handle_message(msg)
        
        # Get chunk response
        chunk_json = await transport.server_receive()
        chunk = parse_message(chunk_json)
        assert isinstance(chunk, RemoteFileChunk)
        assert chunk.handle == handle
        assert chunk.offset == 0
        data = base64.b64decode(chunk.data)
        assert data == test_content[:100]
        
        # Server closes
        close_req = RemoteFileCloseRequest(handle=handle)
        await transport.server_send(close_req.to_json())
        
        # Provider handles close
        msg_json = await transport.client_receive()
        msg = parse_message(msg_json)
        assert isinstance(msg, RemoteFileCloseRequest)
        await provider.handle_message(msg)


    @pytest.mark.asyncio
    async def test_seek_and_read(self, server, provider, transport, temp_dir):
        """Test seek to different positions and read."""
        test_file = temp_dir / "file1.txt"
        test_content = test_file.read_bytes()
        
        # Open
        open_req = RemoteFileOpenRequest(path="/file1.txt", mode="rb")
        await transport.server_send(open_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        handle = resp.handle
        
        # Seek to middle
        seek_req = RemoteFileSeekRequest(handle=handle, offset=500, whence=0)
        await transport.server_send(seek_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        # Read from new position
        read_req = RemoteFileReadRequest(handle=handle, offset=500, length=50)
        await transport.server_send(read_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        chunk_json = await transport.server_receive()
        chunk = parse_message(chunk_json)
        data = base64.b64decode(chunk.data)
        assert data == test_content[500:550]
        
        # Close
        close_req = RemoteFileCloseRequest(handle=handle)
        await transport.server_send(close_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))


    @pytest.mark.asyncio
    async def test_stat_file(self, server, provider, transport, temp_dir):
        """Test stat (metadata) request."""
        stat_req = RemoteFileStatRequest(path="/file1.txt")
        await transport.server_send(stat_req.to_json())
        
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        assert isinstance(resp, RemoteFileStatResponse)
        assert resp.success
        assert resp.size == (temp_dir / "file1.txt").stat().st_size
        assert not resp.is_dir
        assert resp.permissions != ""


    @pytest.mark.asyncio
    async def test_stat_directory(self, server, provider, transport, temp_dir):
        """Test stat on directory."""
        stat_req = RemoteFileStatRequest(path="/subdir")
        await transport.server_send(stat_req.to_json())
        
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        assert isinstance(resp, RemoteFileStatResponse)
        assert resp.success
        assert resp.is_dir


    @pytest.mark.asyncio
    async def test_list_directory(self, server, provider, transport, temp_dir):
        """Test directory listing."""
        list_req = RemoteFileListRequest(path="/", recursive=False)
        await transport.server_send(list_req.to_json())
        
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        # Should get multiple entries + end marker
        entries = []
        while True:
            resp_json = await transport.server_receive()
            resp = parse_message(resp_json)
            if isinstance(resp, RemoteFileListResponse) and resp.entries:
                entries.extend(resp.entries)
            elif isinstance(resp, RemoteFileListResponse) and not resp.entries:
                break  # end marker
        
        names = [e.name for e in entries]
        assert "file1.txt" in names
        assert "file2.bin" in names
        assert "subdir" in names
        
        # Check subdir entry
        subdir_entry = next(e for e in entries if e.name == "subdir")
        assert subdir_entry.is_dir


    @pytest.mark.asyncio
    async def test_list_recursive(self, server, provider, transport, temp_dir):
        """Test recursive directory listing."""
        list_req = RemoteFileListRequest(path="/", recursive=True)
        await transport.server_send(list_req.to_json())
        
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        entries = []
        while True:
            resp_json = await transport.server_receive()
            resp = parse_message(resp_json)
            if isinstance(resp, RemoteFileListResponse) and resp.entries:
                entries.extend(resp.entries)
            elif isinstance(resp, RemoteFileListResponse) and not resp.entries:
                break
        
        paths = [e.path for e in entries]
        assert "subdir/nested.txt" in paths
        assert "subdir/deep/very_deep.txt" in paths


    @pytest.mark.asyncio
    async def test_read_large_file_chunks(self, server, provider, transport, temp_dir):
        """Test reading large file in multiple chunks."""
        test_file = temp_dir / "large.dat"
        test_content = test_file.read_bytes()
        file_size = len(test_content)
        
        # Open
        open_req = RemoteFileOpenRequest(path="/large.dat", mode="rb")
        await transport.server_send(open_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        handle = resp.handle
        assert resp.size == file_size
        
        # Read in chunks
        chunk_size = 8192
        total_read = 0
        while total_read < file_size:
            read_req = RemoteFileReadRequest(
                handle=handle,
                offset=total_read,
                length=min(chunk_size, file_size - total_read)
            )
            await transport.server_send(read_req.to_json())
            msg_json = await transport.client_receive()
            await provider.handle_message(parse_message(msg_json))
            chunk_json = await transport.server_receive()
            chunk = parse_message(chunk_json)
            data = base64.b64decode(chunk.data)
            assert data == test_content[total_read:total_read + len(data)]
            total_read += len(data)
        
        assert total_read == file_size
        
        # Close
        close_req = RemoteFileCloseRequest(handle=handle)
        await transport.server_send(close_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))


    @pytest.mark.asyncio
    async def test_open_nonexistent(self, server, provider, transport):
        """Test opening non-existent file returns error."""
        open_req = RemoteFileOpenRequest(path="/nonexistent.txt", mode="rb")
        await transport.server_send(open_req.to_json())
        
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        assert isinstance(resp, RemoteFileOpenResponse)
        assert not resp.success
        assert resp.error is not None


    @pytest.mark.asyncio
    async def test_invalid_handle(self, server, provider, transport):
        """Test operations on invalid handle."""
        read_req = RemoteFileReadRequest(handle="invalid-handle", offset=0, length=100)
        await transport.server_send(read_req.to_json())
        
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        # Provider doesn't know about server handles, so it won't respond
        # The server will timeout - this is expected behavior


    @pytest.mark.asyncio
    async def test_write_operations(self, server, provider, transport, temp_dir):
        """Test write operations."""
        test_file = temp_dir / "write_test.txt"
        test_file.write_text("original content")
        
        # Open for writing
        open_req = RemoteFileOpenRequest(path="/write_test.txt", mode="r+b")
        await transport.server_send(open_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        handle = resp.handle
        
        # Write new content at offset
        new_data = b"NEW DATA"
        write_req = RemoteFileWriteRequest(
            handle=handle,
            offset=0,
            data=base64.b64encode(new_data).decode()
        )
        await transport.server_send(write_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        # Read back
        read_req = RemoteFileReadRequest(handle=handle, offset=0, length=len(new_data))
        await transport.server_send(read_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        chunk_json = await transport.server_receive()
        chunk = parse_message(chunk_json)
        data = base64.b64decode(chunk.data)
        assert data == new_data
        
        # Close
        close_req = RemoteFileCloseRequest(handle=handle)
        await transport.server_send(close_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        
        # Verify file was actually written
        assert test_file.read_bytes()[:len(new_data)] == new_data


class TestRemoteFileAsync:
    """Test the async file-like interface."""
    
    @pytest.mark.asyncio
    async def test_async_open_read_close(self, server, provider, transport, temp_dir):
        """Test RemoteFileAsync interface."""
        from server.remote_files import RemoteFileAsync
        
        async with RemoteFileAsync(server, "/file1.txt", "rb") as f:
            assert f.size > 0
            assert f.tell() == 0
            
            # Read first 50 bytes
            data = await f.read(50)
            assert len(data) == 50
            assert f.tell() == 50
            
            # Seek and read
            await f.seek(100)
            assert f.tell() == 100
            data = await f.read(30)
            assert len(data) == 30
            
            # Iterate
            await f.seek(0)
            chunks = []
            async for chunk in f:
                chunks.append(chunk)
                if len(chunks) > 5:
                    break
            assert len(chunks) > 0


    @pytest.mark.asyncio
    async def test_remote_open_helper(self, server, provider, transport, temp_dir):
        """Test remote_open helper function."""
        from server.remote_files import remote_open, remote_stat, remote_list
        
        # Test remote_open
        async with await remote_open(server, "/file1.txt") as f:
            data = await f.read(100)
            assert len(data) == 100
        
        # Test remote_stat
        stat = await remote_stat(server, "/file1.txt")
        assert stat["size"] > 0
        assert not stat["is_dir"]
        
        stat = await remote_stat(server, "/subdir")
        assert stat["is_dir"]
        
        # Test remote_list
        entries = await remote_list(server, "/")
        names = [e["name"] for e in entries]
        assert "file1.txt" in names
        assert "subdir" in names


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_read_past_eof(self, server, provider, transport, temp_dir):
        """Test reading past end of file returns empty."""
        open_req = RemoteFileOpenRequest(path="/empty.txt", mode="rb")
        await transport.server_send(open_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        handle = resp.handle
        assert resp.size == 0
        
        # Try to read
        read_req = RemoteFileReadRequest(handle=handle, offset=0, length=100)
        await transport.server_send(read_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        chunk_json = await transport.server_receive()
        chunk = parse_message(chunk_json)
        data = base64.b64decode(chunk.data)
        assert data == b""
        assert chunk.eof
        
        close_req = RemoteFileCloseRequest(handle=handle)
        await transport.server_send(close_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
    
    @pytest.mark.asyncio
    async def test_binary_file_handling(self, server, provider, transport, temp_dir):
        """Test binary file read/write preserves bytes exactly."""
        binary_data = bytes(range(256)) * 4  # 1KB of all byte values
        test_file = temp_dir / "binary_test.bin"
        test_file.write_bytes(binary_data)
        
        open_req = RemoteFileOpenRequest(path="/binary_test.bin", mode="rb")
        await transport.server_send(open_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        resp_json = await transport.server_receive()
        resp = parse_message(resp_json)
        handle = resp.handle
        
        # Read entire file
        read_req = RemoteFileReadRequest(handle=handle, offset=0, length=len(binary_data))
        await transport.server_send(read_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))
        chunk_json = await transport.server_receive()
        chunk = parse_message(chunk_json)
        data = base64.b64decode(chunk.data)
        assert data == binary_data
        
        close_req = RemoteFileCloseRequest(handle=handle)
        await transport.server_send(close_req.to_json())
        msg_json = await transport.client_receive()
        await provider.handle_message(parse_message(msg_json))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])