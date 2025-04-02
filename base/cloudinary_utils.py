import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from django.conf import settings

def upload_image_to_cloudinary(image_file, folder_name):
    """
    Upload một ảnh lên Cloudinary và trả về URL và public_id
    
    Args:
        image_file: File ảnh cần upload
        folder_name: Tên thư mục trên Cloudinary để lưu ảnh
        
    Returns:
        dict: Chứa secure_url và public_id của ảnh đã upload
    """
    try:
        # Upload ảnh lên Cloudinary
        upload_result = cloudinary.uploader.upload(
            image_file,
            folder=folder_name,
            resource_type="auto"
        )
        
        # Lấy URL và public_id
        secure_url = upload_result.get('secure_url')
        public_id = upload_result.get('public_id')
        
        return {
            'secure_url': secure_url,
            'public_id': public_id
        }
    except Exception as e:
        print(f"Error uploading image to Cloudinary: {str(e)}")
        return None

def delete_image_from_cloudinary(public_id):
    """
    Xóa một ảnh từ Cloudinary dựa vào public_id
    
    Args:
        public_id: Public ID của ảnh cần xóa
    """
    try:
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        print(f"Error deleting image from Cloudinary: {str(e)}")

def get_optimized_image_url(public_id, width=None, height=None, crop=None):
    """
    Lấy URL của ảnh đã được tối ưu hóa từ Cloudinary
    
    Args:
        public_id: Public ID của ảnh
        width: Chiều rộng mong muốn (optional)
        height: Chiều cao mong muốn (optional)
        crop: Kiểu cắt ảnh (optional)
        
    Returns:
        str: URL của ảnh đã được tối ưu hóa
    """
    try:
        options = {
            'fetch_format': 'auto',
            'quality': 'auto'
        }
        
        if width:
            options['width'] = width
        if height:
            options['height'] = height
        if crop:
            options['crop'] = crop
            
        url, _ = cloudinary_url(public_id, **options)
        return url
    except Exception as e:
        print(f"Error getting optimized image URL: {str(e)}")
        return None 