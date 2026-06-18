import os
import sys
import urllib.request
import zipfile
import io

def install_ffmpeg():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # ffbinaries static builds URLs for Windows 64-bit
    ffmpeg_url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-win-64.zip"
    ffprobe_url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-win-64.zip"
    
    print("Mendownload ffmpeg.exe (estimasi 26MB)...")
    try:
        # Download and extract ffmpeg
        with urllib.request.urlopen(ffmpeg_url) as response:
            zip_data = response.read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
                zip_ref.extractall(current_dir)
        print("Berhasil mengekstrak ffmpeg.exe.")
        
        print("Mendownload ffprobe.exe (estimasi 22MB)...")
        # Download and extract ffprobe
        with urllib.request.urlopen(ffprobe_url) as response:
            zip_data = response.read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zip_ref:
                zip_ref.extractall(current_dir)
        print("Berhasil mengekstrak ffprobe.exe.")
        
        print("\nFFmpeg berhasil dipasang di folder proyek! yt-dlp sekarang dapat mengonversi unduhan menjadi format MP3.")
        return True
    except Exception as e:
        print(f"\nGagal mendownload FFmpeg: {e}")
        return False

if __name__ == "__main__":
    install_ffmpeg()
