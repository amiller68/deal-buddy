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
                    
                    print(f"Attempt {attempt + 1} failed: {str(e)}")
                    print(f"Retrying in {current_delay} seconds...")
                    
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator

@dataclass
class DocumentContext:
    title: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    running_summary: str = ""
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
    has_confidential: bool = False

class OmEngine:
    def __init__(self, anthropic_client: anthropic.Anthropic, model: str = "claude-3-5-sonnet-20241022"):
        self.anthropic_client = anthropic_client
        self.model = model
        self.debug_dir = Path("debug/om_engine")
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        self.current_run = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_debug_dir = self.debug_dir / self.current_run
        self.current_debug_dir.mkdir(parents=True, exist_ok=True)

    def write_debug(self, filename: str, content: str):
        """Write debug content to a file"""
        with open(self.current_debug_dir / filename, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50} {datetime.now().isoformat()} {'='*50}\n")
            f.write(content)

    @async_retry(retries=3, delay=1.0, backoff=2.0)
    async def generate(self, prompt: str, image: Optional[bytes] = None, max_tokens: int = 8000, temperature: float = 0) -> str:
        """Generate text using the Anthropic model with retries"""
        print("\n=== PROMPT ===")
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        
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
            print("\n=== RESPONSE ===")
            print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
            
            # Write to debug file
            self.write_debug('prompts_and_responses.txt', 
                f"PROMPT:\n{prompt}\n\nIMAGE: {'Yes' if image else 'No'}\n\nRESPONSE:\n{response_text}\n")
            
            return response_text
            
        except Exception as e:
            self.write_debug('errors.txt', 
                f"Error in generate: {str(e)}\nPrompt:\n{prompt}\n")
            raise

    def clean_json_response(self, response_text: str) -> str:
        """Clean and extract JSON from response text"""
        # Remove markdown code blocks if present
        if "```json" in response_text:
            try:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            except IndexError:
                print("Warning: Malformed JSON code block")
        
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
            print(f"Warning: Error cleaning JSON response: {str(e)}")
        
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
            print(f"JSON decode error: {str(e)}")
            if default_value is not None:
                print(f"Using default value: {default_value}")
                return default_value
            raise

    @async_retry(retries=2, delay=1.0, backoff=2.0)
    async def screen_page(self, text: str) -> PageContent:
        """Screen a page for relevance and confidentiality with retries"""
        print(f"\n>>> Screening page (length: {len(text)} chars)")
        response_text = await self.generate(
            PAGE_SCREENING_PROMPT.format(text=text),
            max_tokens=8000
        )
        
        # Parse response with default empty screening result
        response = self.parse_json_response(response_text, {
            "is_relevant": False,
            "has_confidential": True,
            "confidence": 0.0,
            "reason": "Failed to parse response"
        })
        
        page = PageContent(
            text=text,
            image=None,
            is_relevant=response["is_relevant"] and response["confidence"] > 0.7,
            has_confidential=response["has_confidential"]
        )
        print(f"Page relevance: {page.is_relevant}, confidential: {page.has_confidential}")
        return page

    @async_retry(retries=2, delay=1.0, backoff=2.0)
    async def detect_and_extract_tables(self, text: str, image: Optional[bytes], context: DocumentContext) -> None:
        """Extract and normalize tables from text and image with retries"""
        print("\n>>> Detecting tables")
        print(f"Current known tables: {list(context.tables.keys())}")
        
        response_text = ""  # Initialize response_text
        try:
            # First try with a larger context window for complete extraction
            response_text = await self.generate(
                TABLE_DETECTION_PROMPT.format(
                    text=text,
                    known_tables=list(context.tables.keys())
                ),
                image=image,
                max_tokens=8000  # Stay within Claude's limits
            )
            
            # Write raw response for debugging
            self.write_debug('table_responses.json', response_text + "\n")
            
            # If response seems truncated, try again with just the table section
            if '"rent_roll"' in text.lower() and '"rent_roll"' not in response_text.lower():
                print("Rent roll detected but not in response, retrying with focused prompt...")
                rent_roll_text = self.extract_section(text, "rent roll")
                if rent_roll_text:
                    focused_response = await self.generate(
                        "Extract only the rent roll table data from this text. Return as JSON array:\n\n" + rent_roll_text,
                        image=image,
                        max_tokens=8000
                    )
                    # Merge responses
                    response_text = self.merge_json_responses(response_text, focused_response, "rent_roll")

            # Parse response with empty dict as default
            response = self.parse_json_response(response_text, default_value={})
            
            if not response:
                print("No tables found in response")
                return
            
            # Debug print before processing
            print(f"Received tables: {list(response.keys())}")
            
            for table_type, data in response.items():
                if table_type not in context.tables:
                    context.tables[table_type] = []
                    print(f"Created new table type: {table_type}")
                
                if isinstance(data, list):
                    prev_len = len(context.tables[table_type])
                    context.tables[table_type].extend(data)
                    print(f"Added {len(data)} rows to {table_type} (now total: {len(context.tables[table_type])})")
                else:
                    print(f"Warning: Data for {table_type} is not a list: {type(data)}")
                
                # Write extracted tables after each update
                self.write_debug('extracted_tables.json', 
                    json.dumps(context.tables, indent=2) + "\n")
            
            # Debug print after processing
            print(f"Current tables after update: {list(context.tables.keys())}")
            
        except Exception as e:
            print(f"Unexpected error in table extraction: {str(e)}")
            self.write_debug('errors.txt', 
                f"Error processing tables: {str(e)}\nResponse text:\n{response_text}\n")
            raise

    def extract_section(self, text: str, section_name: str) -> Optional[str]:
        """Extract a section of text around a given marker"""
        lines = text.split('\n')
        section_start = None
        section_end = None
        
        # Find the section boundaries
        for i, line in enumerate(lines):
            if section_name.lower() in line.lower():
                section_start = max(0, i - 2)  # Include 2 lines before
                # Look for end markers
                for j in range(i + 1, len(lines)):
                    if any(marker in lines[j].lower() for marker in ['total', 'summary', 'notes', '---']):
                        section_end = j + 1
                        break
                break
        
        if section_start is not None:
            section_end = section_end or len(lines)
            return '\n'.join(lines[section_start:section_end])
        return None

    def merge_json_responses(self, main_response: str, additional_response: str, key: str) -> str:
        """Merge two JSON responses, adding data from additional_response under the specified key"""
        try:
            main_data = json.loads(main_response)
            additional_data = json.loads(additional_response)
            
            if isinstance(additional_data, list):
                main_data[key] = additional_data
            elif isinstance(additional_data, dict):
                main_data[key] = additional_data.get(key, [])
                
            return json.dumps(main_data)
        except json.JSONDecodeError:
            return main_response

    @async_retry(retries=2, delay=1.0, backoff=2.0)
    async def update_summary(self, text: str, context: DocumentContext) -> None:
        """Update running summary with new information with retries"""
        print("\n>>> Updating summary")
        print(f"Current summary length: {len(context.running_summary)}")
        context.running_summary = await self.generate(
            SUMMARY_UPDATE_PROMPT.format(
                current_summary=context.running_summary,
                new_text=text
            ),
            max_tokens=8000
        )
        print(f"New summary length: {len(context.running_summary)}")

    async def process_chunk(self, pages: List[PageContent], context: DocumentContext) -> None:
        """Process a chunk of pages for metadata, tables, and summary"""
        print(f"\n>>> Processing chunk of {len(pages)} pages")
        
        # Combine text from relevant pages
        relevant_pages = [
            page for page in pages 
            if page.is_relevant and not page.has_confidential
        ]
        
        if not relevant_pages:
            print("No relevant pages in chunk, skipping")
            return
            
        relevant_text = "\n".join(page.text for page in relevant_pages)
        
        # Process tables in smaller chunks if text is large
        if len(relevant_text) > 4000:
            print("Large text detected, processing tables in chunks...")
            chunks = self.split_text_into_chunks(relevant_text, 4000)
            for chunk in chunks:
                await self.detect_and_extract_tables(chunk, None, context)
        else:
            # Use the image from the first relevant page that has one
            relevant_image = next((page.image for page in relevant_pages if page.image), None)
            await self.detect_and_extract_tables(relevant_text, relevant_image, context)

        # Process metadata and summary
        if not (context.title and context.address and context.description):
            print("Extracting metadata...")
            metadata = json.loads(await self.generate(METADATA_PROMPT.format(text=relevant_text)))
            if not context.title:
                context.title = metadata.get('title')
            if not context.address:
                context.address = metadata.get('address')
            if not context.description:
                context.description = metadata.get('description')
            print(f"Current metadata - Title: {bool(context.title)}, Address: {bool(context.address)}, Description: {bool(context.description)}")
        
        await self.update_summary(relevant_text, context)

    def split_text_into_chunks(self, text: str, chunk_size: int) -> List[str]:
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
        try:
            context = DocumentContext()
            current_chunk: List[PageContent] = []
            
            print("\n=== Starting PDF Processing ===")
            page_count = 0
            
            # Write initial state
            self.write_debug('processing_log.txt', "Starting PDF processing\n")
            
            async for text, image in extract_pdf(pdf_stream):
                page_count += 1
                print(f"\n--- Processing Page {page_count} ---")
                
                # Write page content for debugging
                self.write_debug('page_contents.txt', 
                    f"\nPAGE {page_count}:\n{text}\n")
                
                page = await self.screen_page(text)
                page.image = image
                current_chunk.append(page)
                
                if (len(current_chunk) >= 3 or 
                    any(marker in text.lower() for marker in ['table', 'summary', 'total'])):
                    print(f"\nProcessing chunk (trigger: {'size limit' if len(current_chunk) >= 3 else 'marker found'})")
                    await self.process_chunk(current_chunk, context)
                    current_chunk = []
            
            if current_chunk:
                print("\nProcessing final chunk")
                await self.process_chunk(current_chunk, context)
            
            # Write final context
            self.write_debug('final_context.json', 
                json.dumps({
                    "title": context.title,
                    "address": context.address,
                    "description": context.description,
                    "summary_length": len(context.running_summary),
                    "tables": {k: len(v) for k, v in context.tables.items()}
                }, indent=2))
            
            return context
            
        except Exception as e:
            self.write_debug('errors.txt', f"Error during processing: {str(e)}\n")
            raise
