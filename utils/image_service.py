"""Image Service Module.

This module provides the ImageService class for handling image download,
processing, and storage using PostgreSQL Large Objects (LOBs).

The service handles:
- Image downloading from external URLs
- Image processing and optimization (resizing, compression)
- Storage in PostgreSQL using Large Objects
- Retrieval and base64 encoding for UI display
- Automatic format conversion and size optimization

Features:
    - Automatic image resizing to max 300x300 pixels
    - JPEG compression with quality optimization
    - Aggressive compression for oversized images
    - Support for JPEG, PNG, WEBP, and GIF formats
    - 2MB maximum file size limit
    - Base64 encoding for UI components
"""

import base64
import io
import requests
from PIL import Image
from typing import Optional, Tuple
from database import Database


class ImageService:
    """Service for handling image download, storage, and retrieval using PostgreSQL Large Objects.
    
    This class provides static methods for managing game images, from download
    through storage to retrieval. Images are processed for optimal size and
    quality before being stored in PostgreSQL as Large Objects.
    
    Storage Strategy:
        - Images are stored as PostgreSQL Large Objects (OIDs)
        - Metadata (MIME type, size) stored in games table
        - Automatic optimization to stay within size limits
        - Fallback compression for large images
        
    Processing Pipeline:
        1. Download image from external URL
        2. Validate format and content type
        3. Resize to maximum dimensions (300x300)
        4. Apply JPEG compression (75% quality)
        5. Additional compression if still too large
        6. Store as Large Object in PostgreSQL
        
    Class Constants:
        MAX_IMAGE_SIZE: Maximum file size (2MB)
        SUPPORTED_FORMATS: Supported image formats
    """
    
    MAX_IMAGE_SIZE = 2 * 1024 * 1024  # 2MB max size
    SUPPORTED_FORMATS = {'JPEG', 'PNG', 'WEBP', 'GIF'}
    
    @staticmethod
    def download_and_store_image(game_id: int, image_url: str) -> bool:
        """Download an image from URL and store it in the database.
        
        Downloads, processes, and stores an image from an external URL.
        The image is optimized for size and quality before storage.
        
        Args:
            game_id (int): ID of the game to store the image for
            image_url (str): URL of the image to download
            
        Returns:
            bool: True if successful, False otherwise
            
        Process:
            1. Download image from URL with timeout
            2. Validate content type and format
            3. Process and optimize image
            4. Store as Large Object in PostgreSQL
            5. Update games table with metadata
            
        Error Handling:
            - Invalid URLs return False
            - Network errors are caught and logged
            - Unsupported formats are rejected
            - Database errors are handled gracefully
        """
        if not image_url or image_url in ['N/A', '']:
            return False
            
        try:
            # Download image
            response = requests.get(image_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                print(f"Invalid content type: {content_type}")
                return False
            
            # Read image data
            image_data = response.content
            
            # Note: We'll compress large images rather than reject them
            if len(image_data) > ImageService.MAX_IMAGE_SIZE:
                print(f"Large image detected: {len(image_data)} bytes - will compress")
            
            # Validate and potentially compress image
            processed_data, mime_type = ImageService._process_image(image_data)
            if not processed_data:
                return False
            
            # If still too large after processing, try more aggressive compression
            if len(processed_data) > ImageService.MAX_IMAGE_SIZE:
                print(f"Image still too large after processing ({len(processed_data)} bytes), trying aggressive compression...")
                processed_data, mime_type = ImageService._aggressive_compress(image_data)
                if not processed_data:
                    return False
            
            # Store in database
            return ImageService._store_image_in_db(game_id, processed_data, mime_type)
            
        except requests.RequestException as e:
            print(f"Failed to download image from {image_url}: {e}")
            return False
        except Exception as e:
            print(f"Error processing image: {e}")
            return False
    
    @staticmethod
    def _process_image(image_data: bytes) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Process and potentially compress an image.
        
        Args:
            image_data: Raw image data
            
        Returns:
            Tuple of (processed_data, mime_type) or (None, None) if failed
        """
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Check format
            if image.format not in ImageService.SUPPORTED_FORMATS:
                print(f"Unsupported format: {image.format}")
                return None, None
            
            # Convert to RGB if needed (for JPEG)
            if image.format == 'JPEG' and image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (max 300x300 for board game images to reduce size)
            max_size = (300, 300)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            
            # Use JPEG for efficiency unless it's PNG with transparency
            if image.format == 'PNG' and image.mode in ('RGBA', 'LA'):
                image.save(output, format='PNG', optimize=True)
                mime_type = 'image/png'
            else:
                # Convert to JPEG for smaller file size
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(output, format='JPEG', quality=75, optimize=True)
                mime_type = 'image/jpeg'
            
            return output.getvalue(), mime_type
            
        except Exception as e:
            print(f"Error processing image: {e}")
            return None, None
    
    @staticmethod
    def _aggressive_compress(image_data: bytes) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Apply aggressive compression for oversized images.
        
        Args:
            image_data: Raw image data
            
        Returns:
            Tuple of (processed_data, mime_type) or (None, None) if failed
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Very aggressive resizing - max 200x200
            max_size = (200, 200)
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Convert to RGB for JPEG
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Try different quality levels until we get under the limit
            for quality in [60, 50, 40, 30, 20]:
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=quality, optimize=True)
                compressed_data = output.getvalue()
                
                print(f"    Trying quality {quality}: {len(compressed_data)} bytes")
                
                if len(compressed_data) <= ImageService.MAX_IMAGE_SIZE:
                    print(f"    Success with quality {quality}!")
                    return compressed_data, 'image/jpeg'
            
            # If still too large even at quality 20, resize more aggressively
            for size in [(150, 150), (100, 100), (80, 80)]:
                image_copy = Image.open(io.BytesIO(image_data))
                if image_copy.mode != 'RGB':
                    image_copy = image_copy.convert('RGB')
                image_copy.thumbnail(size, Image.Resampling.LANCZOS)
                
                output = io.BytesIO()
                image_copy.save(output, format='JPEG', quality=30, optimize=True)
                compressed_data = output.getvalue()
                
                print(f"    Trying size {size}: {len(compressed_data)} bytes")
                
                if len(compressed_data) <= ImageService.MAX_IMAGE_SIZE:
                    print(f"    Success with size {size}!")
                    return compressed_data, 'image/jpeg'
            
            print("    Could not compress image to acceptable size")
            return None, None
            
        except Exception as e:
            print(f"Error in aggressive compression: {e}")
            return None, None
    
    @staticmethod
    def _store_image_in_db(game_id: int, image_data: bytes, mime_type: str) -> bool:
        """
        Store image data in the database using PostgreSQL Large Objects.
        
        Args:
            game_id: ID of the game
            image_data: Processed image data
            mime_type: MIME type of the image
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = Database.get_connection()
            cursor = conn.cursor()
            
            # First, delete any existing image for this game
            cursor.execute("SELECT image_oid FROM games WHERE id = %s", (game_id,))
            result = cursor.fetchone()
            if result and result[0]:
                # Delete the existing Large Object
                cursor.execute("SELECT lo_unlink(%s)", (result[0],))
            
            # Create a new Large Object
            cursor.execute("SELECT lo_create(0)")
            oid = cursor.fetchone()[0]
            
            # Open the Large Object for writing
            cursor.execute("SELECT lo_open(%s, %s)", (oid, 0x20000))  # INV_WRITE = 0x20000
            fd = cursor.fetchone()[0]
            
            # Write data in chunks to avoid memory issues
            chunk_size = 8192
            for i in range(0, len(image_data), chunk_size):
                chunk = image_data[i:i + chunk_size]
                cursor.execute("SELECT lowrite(%s, %s)", (fd, chunk))
            
            # Close the Large Object
            cursor.execute("SELECT lo_close(%s)", (fd,))
            
            # Update the games table with the OID reference
            cursor.execute("""
                UPDATE games 
                SET image_oid = %s, image_mimetype = %s, image_size = %s
                WHERE id = %s
            """, (oid, mime_type, len(image_data), game_id))
            
            conn.commit()
            cursor.close()
            Database.return_connection(conn)
            
            print(f"Stored image for game {game_id}: {len(image_data)} bytes, {mime_type} (OID: {oid})")
            return True
            
        except Exception as e:
            print(f"Error storing image in database: {e}")
            # Clean up on error
            try:
                if 'oid' in locals():
                    cursor.execute("SELECT lo_unlink(%s)", (oid,))
                    conn.commit()
            except:
                pass
            return False
    
    @staticmethod
    def get_image_as_base64(game_id: int) -> Optional[str]:
        """
        Get image data as base64 string for display in Flet.
        
        Args:
            game_id: ID of the game
            
        Returns:
            Base64 encoded image data with data URI prefix, or None if not found
        """
        try:
            conn = Database.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT image_oid, image_mimetype 
                FROM games 
                WHERE id = %s AND image_oid IS NOT NULL
            """, (game_id,))
            
            result = cursor.fetchone()
            
            if not result:
                cursor.close()
                Database.return_connection(conn)
                return None
            
            oid, mime_type = result
            
            # Read the Large Object
            cursor.execute("SELECT lo_open(%s, %s)", (oid, 0x40000))  # INV_READ = 0x40000
            fd = cursor.fetchone()[0]
            
            # Read all data
            image_data = b''
            while True:
                cursor.execute("SELECT loread(%s, %s)", (fd, 8192))
                chunk = cursor.fetchone()[0]
                if not chunk:
                    break
                image_data += chunk
            
            # Close the Large Object
            cursor.execute("SELECT lo_close(%s)", (fd,))
            
            cursor.close()
            Database.return_connection(conn)
            
            if image_data:
                base64_data = base64.b64encode(image_data).decode('utf-8')
                return f"data:{mime_type};base64,{base64_data}"
            
            return None
            
        except Exception as e:
            print(f"Error retrieving image from database: {e}")
            return None
    
    @staticmethod
    def clear_image_data(game_id: int) -> bool:
        """
        Clear image data for a game.
        
        Args:
            game_id: ID of the game
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = Database.get_connection()
            cursor = conn.cursor()
            
            # Get the current OID to delete the Large Object
            cursor.execute("SELECT image_oid FROM games WHERE id = %s", (game_id,))
            result = cursor.fetchone()
            
            if result and result[0]:
                # Delete the Large Object
                cursor.execute("SELECT lo_unlink(%s)", (result[0],))
            
            # Clear the references in the games table
            cursor.execute("""
                UPDATE games 
                SET image_oid = NULL, image_mimetype = NULL, image_size = NULL
                WHERE id = %s
            """, (game_id,))
            
            conn.commit()
            cursor.close()
            Database.return_connection(conn)
            
            return True
            
        except Exception as e:
            print(f"Error clearing image data: {e}")
            return False