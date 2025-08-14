import streamlit as st
import yt_dlp
import os
import tempfile
import re
import io
import time
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="YouTube Downloader",
    page_icon="📺",
    layout="wide"
)

def sanitize_filename(filename):
    """Remove or replace characters that are invalid in filenames"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace multiple spaces with single space
    filename = re.sub(r'\s+', ' ', filename)
    # Trim spaces and limit length
    return filename.strip()[:100]  # Limit filename length

def get_video_info(url):
    """Extract video information and available formats"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get available video qualities - improved logic
            formats = info.get('formats', [])
            video_qualities = set()
            
            for f in formats:
                # Check for video formats (has video codec and height)
                if f.get('vcodec') and f.get('vcodec') != 'none':
                    height = f.get('height')
                    if height and height > 0:
                        quality = f"{height}p"
                        video_qualities.add(quality)
            
            # Convert to list and sort qualities (highest first)
            video_qualities = sorted(list(video_qualities), 
                                   key=lambda x: int(x.replace('p', '')), 
                                   reverse=True)
            
            # If no qualities found, add some common ones based on available formats
            if not video_qualities:
                for f in formats:
                    format_note = f.get('format_note', '').lower()
                    if 'tiny' in format_note:
                        video_qualities.append('144p')
                    elif 'small' in format_note:
                        video_qualities.append('240p')
                    elif 'medium' in format_note:
                        video_qualities.append('360p')
                    elif 'large' in format_note:
                        video_qualities.append('480p')
                    elif 'hd720' in format_note:
                        video_qualities.append('720p')
                    elif 'hd1080' in format_note:
                        video_qualities.append('1080p')
                
                video_qualities = sorted(list(set(video_qualities)), 
                                       key=lambda x: int(x.replace('p', '')), 
                                       reverse=True)
            
            return {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'video_qualities': video_qualities,
                'thumbnail': info.get('thumbnail', ''),
                'id': info.get('id', '')
            }
    except Exception as e:
        st.error(f"Error extracting video info: {str(e)}")
        return None

def download_audio_to_memory(url):
    """Download audio as MP3 to memory for direct download"""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, "audio")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': temp_file_path + '.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Find the downloaded file
                mp3_file = temp_file_path + '.mp3'
                if os.path.exists(mp3_file):
                    # Read file into memory
                    with open(mp3_file, 'rb') as f:
                        file_data = f.read()
                    
                    filename = sanitize_filename(info['title']) + '.mp3'
                    return file_data, filename
                else:
                    st.error("MP3 file not found after conversion")
                    return None, None
                    
    except Exception as e:
        st.error(f"Error downloading audio: {str(e)}")
        return None, None

def download_video_to_memory(url, quality="best"):
    """Download video as MP4 to memory for direct download"""
    try:
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, "video")
            
            # Format selection based on quality
            if quality == "best":
                format_selector = 'best[ext=mp4]/best'
            else:
                height = quality.replace('p', '')
                format_selector = f'best[height<={height}][ext=mp4]/best[height<={height}]/best'
            
            ydl_opts = {
                'format': format_selector,
                'outtmpl': temp_file_path + '.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Find the downloaded file (could be .mp4 or other format)
                downloaded_files = [f for f in os.listdir(temp_dir) if f.startswith("video")]
                
                if downloaded_files:
                    downloaded_file = os.path.join(temp_dir, downloaded_files[0])
                    
                    # Read file into memory
                    with open(downloaded_file, 'rb') as f:
                        file_data = f.read()
                    
                    filename = sanitize_filename(info['title']) + '.mp4'
                    return file_data, filename
                else:
                    st.error("Video file not found after download")
                    return None, None
                    
    except Exception as e:
        st.error(f"Error downloading video: {str(e)}")
        return None, None

def format_duration(seconds):
    """Convert seconds to readable format"""
    if seconds:
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    return "Unknown"

def format_views(views):
    """Format view count"""
    if views:
        if views >= 1_000_000:
            return f"{views/1_000_000:.1f}M views"
        elif views >= 1_000:
            return f"{views/1_000:.1f}K views"
        else:
            return f"{views} views"
    return "Unknown views"

def format_file_size(size_bytes):
    """Format file size in readable format"""
    if size_bytes == 0:
        return "0B"
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

# Main Streamlit App
def main():
    st.title("🎥 YouTube Downloader ")
    st.markdown("Download YouTube videos as MP3 or MP4 directly to your device")
    
    # URL input
    url = st.text_input("📋 Enter YouTube URL:", placeholder="https://www.youtube.com/watch?v=...")
    enter_clicked = st.button("Enter", type="primary", use_container_width=True)
    if url:
        # Validate URL
        if not ("youtube.com/watch" in url or "youtu.be/" in url or "youtube.com/shorts" in url):
            st.error("Please enter a valid YouTube URL")
            return
        
        # Get video information
        with st.spinner("Fetching video information..."):
            video_info = get_video_info(url)
        
        if video_info:
            # Display video information
            col1, col2 = st.columns([1, 2])
            
            with col1:
                if video_info['thumbnail']:
                    st.image(video_info['thumbnail'], width=300)
            
            with col2:
                st.subheader(video_info['title'])
                st.write(f"**Uploader:** {video_info['uploader']}")
                st.write(f"**Duration:** {format_duration(video_info['duration'])}")
                st.write(f"**Views:** {format_views(video_info['view_count'])}")
            
            st.divider()
            
            # Download options
            st.subheader("📥 Download Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # MP3 Download
                st.markdown("### 🎵 Audio (MP3)")
                st.write("High quality audio (192 kbps)")
                
                if st.button("Download MP3", type="primary", use_container_width=True, key="mp3_btn"):
                    download_placeholder = st.empty()
                    progress_bar = st.progress(0)
                    
                    with download_placeholder:
                        st.info("⏳ Preparing audio download...")
                    
                    progress_bar.progress(25)
                    file_data, filename = download_audio_to_memory(url)
                    
                    if file_data and filename:
                        progress_bar.progress(100)
                        file_size = format_file_size(len(file_data))
                        
                        with download_placeholder:
                            st.success(f"✅ Audio ready for download!")
                            st.info(f"📁 File: {filename}")
                            st.info(f"📊 Size: {file_size}")
                        
                        # Create download button
                        st.download_button(
                            label="📥 Download MP3 File",
                            data=file_data,
                            file_name=filename,
                            mime="audio/mpeg",
                            use_container_width=True,
                            type="secondary"
                        )
                        
                        st.success("🎉 Click the download button above to save to your device!")
                    else:
                        progress_bar.empty()
                        download_placeholder.error("❌ Failed to prepare audio download")
            
            with col2:
                # MP4 Download
                st.markdown("### 🎬 Video (MP4)")
                
                # Quality selection
                qualities = ["best"] + video_info['video_qualities']
                selected_quality = st.selectbox(
                    "Select Quality:",
                    qualities,
                    format_func=lambda x: f"Best Available" if x == "best" else x
                )
                
                if st.button("Download MP4", type="primary", use_container_width=True, key="mp4_btn"):
                    download_placeholder = st.empty()
                    progress_bar = st.progress(0)
                    
                    with download_placeholder:
                        st.info(f"⏳ Preparing video download ({selected_quality})...")
                    
                    progress_bar.progress(25)
                    file_data, filename = download_video_to_memory(url, selected_quality)
                    
                    if file_data and filename:
                        progress_bar.progress(100)
                        file_size = format_file_size(len(file_data))
                        
                        with download_placeholder:
                            st.success(f"✅ Video ready for download!")
                            st.info(f"📁 File: {filename}")
                            st.info(f"📊 Size: {file_size}")
                            st.info(f"🎯 Quality: {selected_quality}")
                        
                        # Create download button
                        st.download_button(
                            label="📥 Download MP4 File",
                            data=file_data,
                            file_name=filename,
                            mime="video/mp4",
                            use_container_width=True,
                            type="secondary"
                        )
                        
                        st.success("🎉 Click the download button above to save to your device!")
                    else:
                        progress_bar.empty()
                        download_placeholder.error("❌ Failed to prepare video download")
    
    # Instructions
    st.divider()
    st.markdown("""
    ### 📖 How to Use:
    1. **Paste URL**: Enter any YouTube video URL in the input field
    2. **Preview**: View video information, thumbnail, and available qualities
    3. **Choose Format**: Select MP3 for audio or MP4 for video
    4. **Select Quality**: For videos, choose your preferred resolution
    5. **Download**: Click download button and wait for processing
    6. **Save**: Use the download button to save directly to your device
    
    ### ✨ Features:
    - 🎵 **High-quality MP3**: 192 kbps audio extraction
    - 🎬 **Multiple resolutions**: Choose from available video qualities
    - 📱 **Direct downloads**: Files download straight to your device
    - 🖼️ **Preview**: See thumbnail and video details before downloading
    - 📊 **File info**: View file size before downloading
    
    
    ### ⚠️ Important Notes:
    - Downloads go directly to your device's download folder
    - Processing time depends on video length and quality
    - Large files may take longer to prepare
    - Respect YouTube's Terms of Service
    - Some videos may have download restrictions
    
    """)
    
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <p style='font-size: 16px; color: #666; font-weight: 500;'>
            Developed and Hosted by <span style='color: #1a73e8; font-weight: 600;'>Larwin J</span> 😎</br>
            Anonymous
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()