from abc import ABC, abstractmethod
from typing import AsyncIterator, Tuple, Any
import asyncio

class BaseEngine(ABC):
    @abstractmethod
    async def extract_text(self, stream: AsyncIterator[bytes]) -> str:
        """Extract text from the byte stream"""
        pass

    @abstractmethod
    async def extract_images(self, stream: AsyncIterator[bytes]) -> list[bytes]:
        """Extract images from the byte stream"""
        pass

    async def process_stream(self, stream: AsyncIterator[bytes]) -> Tuple[str, list[bytes]]:
        """Process stream in parallel, extracting both text and images"""
        # Create two copies of the stream
        text_stream, image_stream = tee_async_iterator(stream)
        
        # Process text and images in parallel
        text_task = asyncio.create_task(self.extract_text(text_stream))
        images_task = asyncio.create_task(self.extract_images(image_stream))
        
        # Wait for both tasks to complete
        text, images = await asyncio.gather(text_task, images_task)
        return text, images

async def tee_async_iterator(aiter: AsyncIterator[Any]) -> Tuple[AsyncIterator[Any], AsyncIterator[Any]]:
    """Split an async iterator into two identical iterators"""
    buffer: list[Any] = []
    iterators_alive = 2
    
    async def gen():
        nonlocal iterators_alive
        pos = 0
        try:
            while True:
                if pos < len(buffer):
                    yield buffer[pos]
                    pos += 1
                else:
                    try:
                        item = await aiter.__anext__()
                        buffer.append(item)
                        yield item
                        pos += 1
                    except StopAsyncIteration:
                        break
        finally:
            iterators_alive -= 1
            if iterators_alive == 0:
                buffer.clear()
    
    return gen(), gen()