import anthropic
from typing import BinaryIO, Optional, Dict, List, Any, AsyncGenerator, Tuple
from dataclasses import dataclass
import json
import asyncio
from .pdf import extract_pdf
from .prompts import (
    METADATA_PROMPT, 
    TABLE_DETECTION_PROMPT, 
    SUMMARY_UPDATE_PROMPT, 
    PAGE_SCREENING_PROMPT
)
import os
from datetime import datetime
from pathlib import Path
import functools
import time
from typing import TypeVar, Callable, Any, ParamSpec
import base64
from src.database.models.om import OmStatus  
from typing import Callable, Awaitable

# Constants
METADATA_MAX_TOKENS = 1500
TABLE_DETECTION_MAX_TOKENS = 8000
SUMMARY_UPDATE_MAX_TOKENS = 1000
PAGE_SCREENING_MAX_TOKENS = 1000
CHUNK_PAGE_LIMIT = 3
TEXT_CHUNK_SIZE = 4000


T = TypeVar('T')
P = ParamSpec('P')

def async_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator for async functions with exponential backoff
    
    Args:
        retries: Number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        raise
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator

@dataclass
class DocumentContext:
    title: Optional[str] = None
    address: Optional[str] = None
    square_feet: Optional[int] = None
    total_units: Optional[int] = None
    property_type: Optional[str] = None
    description: Optional[str] = None
    running_summary: str = ""
    metadata: Dict[str, any] = None
    tables: Dict[str, List[Dict[str, Any]]] = None
    current_page: int = 0
    
    def __post_init__(self):
        if self.tables is None:
            self.tables = {}

@dataclass
class PageContent:
    text: str
    image: Optional[bytes]
    is_relevant: bool = False
    reason: str = ""

@dataclass
class ProgressEvent:
    status: OmStatus
    current_page: int
    total_pages: int
    error: str | None = None

# TODO: long term debugging strategy
class OmEngine:
    # enable async callbacks
    def __init__(
        self, 
        anthropic_client: anthropic.Anthropic, 
        model: str = "claude-3-5-sonnet-20241022",
        progress_callback: Callable[[ProgressEvent], Awaitable[None]] | None = None
    ):
        self.anthropic_client = anthropic_client
        self.model = model
        self.progress_callback = progress_callback

    async def emit_progress(self, event: ProgressEvent):
        """Emit a progress event if callback is configured"""
        if self.progress_callback:
            await self.progress_callback(event)

    @async_retry(retries=3, delay=1.0, backoff=2.0)
    async def generate(self, prompt: str, image: Optional[bytes] = None, max_tokens: int = 8000, temperature: float = 0) -> str:
        """Generate text using the Anthropic model with retries"""
        try:
            messages_content = [{"type": "text", "text": prompt}]
            if image:
                messages_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64.b64encode(image).decode('utf-8')
                    }
                })
            response = self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{
                    "role": "user",
                    "content": messages_content
                }]
            )
            response_text = response.content[0].text
            return response_text
            
        except Exception as e:
            raise

    def clean_json_response(self, response_text: str) -> str:
        """Clean and extract JSON from response text"""
        # Remove markdown code blocks if present
        if "```json" in response_text:
            try:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            except IndexError:
                pass
        
        # Remove any explanatory text before or after JSON
        try:
            # Find first { or [ and last } or ]
            start_idx = min(
                (response_text.find('{') if '{' in response_text else len(response_text)),
                (response_text.find('[') if '[' in response_text else len(response_text))
            )
            end_idx = max(
                (response_text.rfind('}') if '}' in response_text else -1),
                (response_text.rfind(']') if ']' in response_text else -1)
            )
            
            if start_idx < end_idx:
                response_text = response_text[start_idx:end_idx + 1]
        except Exception as e:
            pass
        
        # Handle empty or invalid JSON structures
        if response_text.strip() in ['{}', '[]', '']:
            return '{}'
            
        return response_text

    def parse_json_response(self, response_text: str, default_value: Any = None) -> Any:
        """Parse JSON response with error handling"""
        try:
            cleaned_text = self.clean_json_response(response_text)
            return json.loads(cleaned_text)
        except json.JSONDecodeError as e:
            if default_value is not None:
                return default_value
            raise

    @async_retry(retries=2, delay=1.0, backoff=2.0)
    async def screen_page(self, text: str) -> PageContent:
        """Screen a page for relevance with retries"""
        response_text = await self.generate(
            PAGE_SCREENING_PROMPT.format(text=text),
            max_tokens=PAGE_SCREENING_MAX_TOKENS
        )
        
        # Parse response with default empty screening result
        response = self.parse_json_response(response_text, {
            "is_relevant": False,
            "confidence": 0.0,
            "reason": "failed-to-parse"
        })

        # TODO: maybe i should just make this binary 
        page = PageContent(
            text=text,
            image=None,
            is_relevant=response["is_relevant"] and response["confidence"] > 0.7,
            reason=response["reason"]
        )
        return page

    @async_retry(retries=2, delay=1.0, backoff=2.0)
    async def detect_and_extract_tables(self, text: str, image: Optional[bytes], context: DocumentContext) -> None:
        """Extract and normalize tables from text and image with retries"""
        
        response_text = ""  # Initialize response_text
        try:
            # First try with a larger context window for complete extraction
            response_text = await self.generate(
                TABLE_DETECTION_PROMPT.format(
                    text=text,
                    known_tables=list(context.tables.keys())
                ),
                image=image,
                max_tokens=TABLE_DETECTION_MAX_TOKENS
            )
            
            
            # Parse response with empty dict as default
            response = self.parse_json_response(response_text, default_value={})
            
            if not response:
                return
            
            for table_type, data in response.items():
                if table_type not in context.tables:
                    context.tables[table_type] = []
                
                if isinstance(data, list):
                    context.tables[table_type].extend(data)
            
        except Exception as e:
            raise



    @async_retry(retries=2, delay=1.0, backoff=2.0)
    async def update_summary(self, text: str, context: DocumentContext) -> None:
        """Update running summary with new information with retries"""
        context.running_summary = await self.generate(
            SUMMARY_UPDATE_PROMPT.format(
                current_summary=context.running_summary,
                new_text=text
            ),
            max_tokens=SUMMARY_UPDATE_MAX_TOKENS
        )

    async def process_chunk(self, pages: List[PageContent], context: DocumentContext) -> None:
        """Process a chunk of pages for metadata, tables, and summary"""
        # Combine text from relevant pages
        relevant_pages = [
            page for page in pages 
            if page.is_relevant
        ]
        
        if not relevant_pages:
            return
            
        relevant_text = "\n".join(page.text for page in relevant_pages)
        # Collect all images from relevant pages
        relevant_images = [page.image for page in relevant_pages if page.image]
        
        # Process tables in smaller chunks if text is large
        if len(relevant_text) > TEXT_CHUNK_SIZE:
            chunks = self.split_text_into_chunks(relevant_text, TEXT_CHUNK_SIZE)
            for i, chunk in enumerate(chunks):
                # Use corresponding images for each chunk if available
                chunk_images = relevant_images[i:i+1] if i < len(relevant_images) else []
                await self.process_chunk_data(chunk, chunk_images, context)
        else:
            await self.process_chunk_data(relevant_text, relevant_images, context)

        await self.update_summary(relevant_text, context)

    async def process_chunk_data(self, text: str, images: List[bytes], context: DocumentContext) -> None:
        """Process both tables and metadata from a chunk of text and its images"""
        # Process each image with both metadata and table detection
        for image in images:
            # Try to extract metadata if needed
            if not (context.title and context.address and context.description):
                metadata_response = await self.generate(
                    METADATA_PROMPT.format(text=text),
                    image=image,
                    max_tokens=METADATA_MAX_TOKENS
                )
                try:
                    metadata = self.parse_json_response(metadata_response)
                    if not context.title:
                        context.title = metadata.get("title")
                    if not context.address:
                        context.address = metadata.get("address")
                    if not context.description:
                        context.description = metadata.get("description")
                    if not context.square_feet:
                        context.square_feet = metadata.get("square_feet")
                    if not context.total_units:
                        context.total_units = metadata.get("total_units")
                    if not context.property_type:
                        context.property_type = metadata.get("property_type")
                    # fill in the rest of the metadata by associating other new fields with the existing generic fields
                    for key, value in metadata.items():
                        if key not in context.metadata:
                            context.metadata[key] = value
                except Exception as e:
                    raise

            # Extract tables
            table_response = await self.generate(
                TABLE_DETECTION_PROMPT.format(
                    text=text,
                    known_tables=list(context.tables.keys())
                ),
                image=image,
                max_tokens=TABLE_DETECTION_MAX_TOKENS
            )
            
            try:
                tables = self.parse_json_response(table_response, default_value={})
                for table_type, data in tables.items():
                    if isinstance(data, list):
                        if table_type not in context.tables:
                            context.tables[table_type] = []
                        context.tables[table_type].extend(data)
                
            except Exception as e:
                raise

    def split_text_into_chunks(self, text: str, chunk_size: int = TEXT_CHUNK_SIZE) -> List[str]:
        """Split text into chunks while trying to maintain table integrity"""
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            if current_size + line_size > chunk_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            current_chunk.append(line)
            current_size += line_size
            
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
            
        return chunks

    async def process_pdf(self, pdf_stream: BinaryIO):
        """Process a PDF document and extract structured data"""
        total_pages = 0
        try:
            context = DocumentContext()
            current_chunk: List[PageContent] = []
            
            page_count = 0
            
            async for text, image, tp in extract_pdf(pdf_stream):
                total_pages = tp
                page_count += 1
                # Emit progress update
                await self.emit_progress(ProgressEvent(
                    status=OmStatus.PROCESSING,
                    current_page=page_count,
                    total_pages=total_pages,
                ))
                
                page = await self.screen_page(text)
                page.image = image
                current_chunk.append(page)
                
                if len(current_chunk) >= CHUNK_PAGE_LIMIT:
                    await self.process_chunk(current_chunk, context)
                    current_chunk = []
            if current_chunk:
                await self.process_chunk(current_chunk, context)
            
            # Emit completion status
            await self.emit_progress(ProgressEvent(
                status=OmStatus.PROCESSED,
                current_page=total_pages,
                total_pages=total_pages,
                percentage=100
            ))
            
            return context
            
        except Exception as e:
            # Emit error status
            await self.emit_progress(ProgressEvent(
                status=OmStatus.FAILED,
                current_page=page_count,
                total_pages=total_pages,
                error=str(e)
            ))
            raise
