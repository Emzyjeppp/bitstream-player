import os
import sys
import time
import ctypes
import threading
import yt_dlp

# Force stdout/stderr to UTF-8 to handle Unicode box drawing characters on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
if sys.stderr.encoding.lower() != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# --- CONSTANTS & CONFIG ---
DESIGN_VARIANCE = 5
MOTION_INTENSITY = 4
VISUAL_DENSITY = 5

# --- ANSI COLOR SETUP ---
def enable_ansi():
    if os.name == 'nt':
        kernel32 = ctypes.windll.kernel32
        hStdOut = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
        if hStdOut == -1:
            return False
        mode = ctypes.c_ulong()
        if not kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode)):
            return False
        mode.value |= 4 # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if not kernel32.SetConsoleMode(hStdOut, mode):
            return False
    return True

HAS_COLOR = enable_ansi()

COLOR_TITLE = "\033[1;38;2;0;229;255m" if HAS_COLOR else ""      # Bold Electric Cyan
COLOR_ACCENT = "\033[38;2;0;229;255m" if HAS_COLOR else ""        # Electric Cyan
COLOR_MUTED = "\033[38;2;120;120;130m" if HAS_COLOR else ""       # Cool Slate Gray
COLOR_BORDER = "\033[38;2;70;80;90m" if HAS_COLOR else ""         # Dark Slate Border
COLOR_SUCCESS = "\033[38;2;40;200;120m" if HAS_COLOR else ""      # Emerald Green
COLOR_ERROR = "\033[38;2;255;80;100m" if HAS_COLOR else ""        # Coral Red
COLOR_HIGHLIGHT_BG = "\033[48;2;20;32;45m" if HAS_COLOR else ""   # Dark Slate Blue Background
COLOR_HIGHLIGHT_FG = "\033[1;38;2;0;229;255m" if HAS_COLOR else "" # Highlight Bold Cyan
COLOR_RESET = "\033[0m" if HAS_COLOR else ""

# --- MCI WINDOWS MEDIA BACKEND ---
winmm = ctypes.windll.winmm

def mci_send(command):
    buffer = ctypes.create_string_buffer(255)
    error = winmm.mciSendStringA(command.encode('utf-8'), buffer, 254, 0)
    if error:
        err_buffer = ctypes.create_string_buffer(255)
        winmm.mciGetErrorStringA(error, err_buffer, 254)
        return False, err_buffer.value.decode('utf-8', errors='ignore').strip()
    return True, buffer.value.decode('utf-8', errors='ignore').strip()

# --- STATE MANAGEMENT ---
playlist = []
duration_cache = {}
current_track_index = -1
is_playing = False
is_paused = False
user_stopped = True
volume = 80
muted = False
running = True

# Download queue status
download_status = ""
download_info = ""

# Status message shown after command execution
status_msg = ""
status_type = "info" # "info", "success", "error"

# --- HELPER FUNCTIONS ---
def get_playlist():
    music_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
    if not os.path.exists(music_dir):
        os.makedirs(music_dir)
    files = []
    for f in os.listdir(music_dir):
        if f.lower().endswith(('.mp3', '.wav', '.m4a')):
            files.append(os.path.join(music_dir, f))
    return sorted(files)

def get_audio_length_mci(filepath):
    temp_alias = "temp_len"
    filepath = filepath.replace("\\", "/")
    # Close first just in case
    mci_send(f"close {temp_alias}")
    success, _ = mci_send(f'open "{filepath}" type mpegvideo alias {temp_alias}')
    if not success:
        success, _ = mci_send(f'open "{filepath}" alias {temp_alias}')
    if not success:
        return 0
    success, response = mci_send(f"status {temp_alias} length")
    mci_send(f"close {temp_alias}")
    if success:
        try:
            return int(response)
        except ValueError:
            return 0
    return 0

def get_track_duration(filepath):
    if filepath in duration_cache:
        return duration_cache[filepath]
    duration = get_audio_length_mci(filepath)
    if duration > 0:
        duration_cache[filepath] = duration
    return duration

def format_time(ms):
    seconds = int(ms / 1000)
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def get_current_song_name():
    if 0 <= current_track_index < len(playlist):
        return os.path.basename(playlist[current_track_index])
    return "None"

def get_mci_position():
    success, response = mci_send("status my_music position")
    if success:
        try:
            return int(response)
        except ValueError:
            return 0
    return 0

def get_mci_length():
    if 0 <= current_track_index < len(playlist):
        # Prefer cache
        cached = get_track_duration(playlist[current_track_index])
        if cached > 0:
            return cached
    success, response = mci_send("status my_music length")
    if success:
        try:
            return int(response)
        except ValueError:
            return 0
    return 0

def get_mci_mode():
    success, response = mci_send("status my_music mode")
    if success:
        return response.lower()
    return "stopped"

def set_mci_volume(vol_pct):
    mci_vol = int((vol_pct / 100) * 1000)
    mci_send(f"setaudio my_music volume to {mci_vol}")

# --- MUSIC CONTROLS ---
def load_and_play(filepath):
    global is_playing, is_paused, user_stopped
    
    mci_send("stop my_music")
    mci_send("close my_music")
    
    filepath = filepath.replace("\\", "/")
    success, response = mci_send(f'open "{filepath}" type mpegvideo alias my_music')
    if not success:
        # Fallback to auto-detecting device type (handles WAV as waveaudio if mpegvideo fails)
        success, response = mci_send(f'open "{filepath}" alias my_music')
    if not success:
        return False, f"MCI Open Error: {response}"
        
    set_mci_volume(volume)
    if muted:
        mci_send("setaudio my_music mute on")
        
    success, response = mci_send("play my_music")
    if not success:
        mci_send("close my_music")
        return False, f"MCI Play Error: {response}"
        
    is_playing = True
    is_paused = False
    user_stopped = False
    return True, "Playing"

def play_track(index):
    global current_track_index, status_msg, status_type
    if not playlist:
        status_msg = "Playlist kosong! Letakkan musik di folder 'music/' atau download dari YouTube."
        status_type = "error"
        return
    if index < 0 or index >= len(playlist):
        status_msg = f"Indeks tidak valid! Pilih antara 1 hingga {len(playlist)}."
        status_type = "error"
        return
    
    current_track_index = index
    song_path = playlist[current_track_index]
    success, msg = load_and_play(song_path)
    if success:
        status_msg = f"Memutar: {os.path.basename(song_path)}"
        status_type = "success"
    else:
        status_msg = msg
        status_type = "error"

def pause_track():
    global is_paused, status_msg, status_type
    if not is_playing:
        status_msg = "Tidak ada musik yang sedang diputar."
        status_type = "error"
        return
    if is_paused:
        status_msg = "Musik sudah dalam kondisi dijeda (paused)."
        status_type = "info"
        return
    
    success, response = mci_send("pause my_music")
    if success:
        is_paused = True
        status_msg = "Musik dijeda (paused)."
        status_type = "success"
    else:
        status_msg = f"Gagal menjeda: {response}"
        status_type = "error"

def resume_track():
    global is_paused, status_msg, status_type
    if not is_playing:
        # If stopped, try playing current or first track
        if current_track_index >= 0:
            play_track(current_track_index)
        else:
            play_track(0)
        return
    if not is_paused:
        status_msg = "Musik sedang berputar."
        status_type = "info"
        return
    
    success, response = mci_send("play my_music")
    if success:
        is_paused = False
        status_msg = "Melanjutkan pemutaran musik."
        status_type = "success"
    else:
        status_msg = f"Gagal melanjutkan: {response}"
        status_type = "error"

def stop_track():
    global is_playing, is_paused, user_stopped, status_msg, status_type
    if not is_playing and get_mci_mode() == "stopped":
        status_msg = "Musik sudah dihentikan."
        status_type = "info"
        return
        
    mci_send("stop my_music")
    is_playing = False
    is_paused = False
    user_stopped = True
    status_msg = "Pemutaran musik dihentikan."
    status_type = "success"

def next_track():
    global status_msg, status_type
    if not playlist:
        status_msg = "Playlist kosong."
        status_type = "error"
        return
    next_idx = (current_track_index + 1) % len(playlist)
    play_track(next_idx)

def prev_track():
    global status_msg, status_type
    if not playlist:
        status_msg = "Playlist kosong."
        status_type = "error"
        return
    prev_idx = (current_track_index - 1) % len(playlist)
    play_track(prev_idx)

def set_volume(vol_val):
    global volume, status_msg, status_type
    if vol_val < 0 or vol_val > 100:
        status_msg = "Volume harus bernilai antara 0-100."
        status_type = "error"
        return
    volume = vol_val
    if is_playing:
        set_mci_volume(volume)
    status_msg = f"Volume diatur ke: {volume}%"
    status_type = "success"

def toggle_mute():
    global muted, status_msg, status_type
    muted = not muted
    if is_playing:
        cmd = "setaudio my_music mute on" if muted else "setaudio my_music mute off"
        mci_send(cmd)
    status_msg = "Suara dinonaktifkan (Muted)" if muted else "Suara diaktifkan (Unmuted)"
    status_type = "success"

# --- YOUTUBE DOWNLOADER ---
def ytdl_hook(d):
    global download_status
    if d['status'] == 'downloading':
        pct = d.get('_percent_str', '0%').strip()
        # Clean control characters from yt-dlp output
        pct = ''.join(c for c in pct if c.isdigit() or c in ['.', '%'])
        download_status = f"Mengunduh: {pct}"
    elif d['status'] == 'finished':
        download_status = "Memproses berkas audio..."

def download_thread_proc(url):
    global download_status, download_info, playlist, status_msg, status_type
    download_status = "Menghubungi YouTube..."
    download_info = ""
    
    music_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(music_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True, # Safe ASCII filenames without spaces
        'noplaylist': True,
        'progress_hooks': [ytdl_hook],
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': os.path.dirname(os.path.abspath(__file__)),
        'socket_timeout': 15,          # Avoid hanging indefinitely
        'nocheckcertificate': True,    # Bypass SSL verification issues
        'geo_bypass': True,            # Help with regional restriction stalls
        'youtube_include_dash_manifest': False, # Speeds up connection by bypassing DASH
        'youtube_include_hls_playlist': False,  # Speeds up connection by bypassing HLS
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info to get clean title
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # The postprocessor extracts it to .mp3, so change extension in display name
            basename = os.path.splitext(os.path.basename(filename))[0] + ".mp3"
            download_status = "Selesai"
            download_info = basename
            # Refresh playlist
            playlist = get_playlist()
            # Push dynamic update status
            status_msg = f"[DOWNLOAD SUKSES] Berhasil mengunduh: {basename}"
            status_type = "success"
    except Exception as e:
        download_status = "Gagal"
        download_info = str(e)[:40]
        status_msg = f"[DOWNLOAD GAGAL] {str(e)}"
        status_type = "error"

def start_download(url):
    global download_status, status_msg, status_type
    if download_status.startswith("Mengunduh") or download_status.startswith("Menghubungi"):
        status_msg = "Ada proses download yang sedang berjalan. Tunggu hingga selesai."
        status_type = "error"
        return
        
    thread = threading.Thread(target=download_thread_proc, args=(url,))
    thread.daemon = True
    thread.start()
    status_msg = "Download dimulai di latar belakang. Anda tetap bisa memutar musik."
    status_type = "info"

# --- BACKGROUND THREADS ---
def auto_play_next_loop():
    global current_track_index, is_playing, is_paused
    while running:
        time.sleep(0.5)
        # Check if playing according to our state but stopped according to MCI
        if is_playing and not is_paused:
            if get_mci_mode() == "stopped" and not user_stopped:
                # Track finished naturally, auto-play next
                next_track()

def title_bar_update_loop():
    while running:
        if is_playing:
            pos = get_mci_position()
            length = get_mci_length()
            mode = get_mci_mode()
            
            status_symbol = "▶" if mode == "playing" else "▮▮"
            song_name = get_current_song_name()
            
            if length > 0:
                pos_str = format_time(pos)
                len_str = format_time(length)
                pct = int((pos / length) * 100)
                title = f"[{status_symbol}] {song_name} ({pos_str} / {len_str}) | Vol: {volume}% - BitStream Player"
            else:
                title = f"[{status_symbol}] {song_name} | Vol: {volume}% - BitStream Player"
        else:
            title = "BitStream Player (Stopped)"
            
        if download_status and not download_status.startswith("Selesai") and not download_status.startswith("Gagal"):
            title = f"[{download_status}] " + title
            
        ctypes.windll.kernel32.SetConsoleTitleW(title)
        time.sleep(1.0)

# --- TERMINAL UI RENDERER ---
def make_progress_bar(pos, length):
    bar_width = 30
    if length <= 0:
        return f"{COLOR_MUTED}───●" + "─" * (bar_width - 4) + f"{COLOR_RESET}"
    pct = pos / length
    if pct > 1.0:
        pct = 1.0
    dot_pos = int(pct * bar_width)
    if dot_pos >= bar_width:
        dot_pos = bar_width - 1
    
    before = f"{COLOR_ACCENT}" + "─" * dot_pos
    dot = f"{COLOR_ACCENT}●"
    after = f"{COLOR_MUTED}" + "─" * (bar_width - dot_pos - 1)
    
    return f"{before}{dot}{after}{COLOR_RESET}"

def make_volume_bar(vol):
    bar_width = 10
    filled = int(vol / 10)
    bar = f"{COLOR_ACCENT}" + "▮" * filled + f"{COLOR_MUTED}" + "░" * (bar_width - filled)
    return f"{COLOR_MUTED}[ {bar}{COLOR_MUTED} ]{COLOR_RESET}"

def draw_ui():
    # Clear screen cleanly
    os.system('cls' if os.name == 'nt' else 'clear')
    
    box_width = 60
    
    # Header Card
    print(f"{COLOR_BORDER}┌" + "─" * box_width + "┐" + f"{COLOR_RESET}")
    print(f"{COLOR_BORDER}│{COLOR_TITLE}                 BITSTREAM PLAYER v1.0                      {COLOR_BORDER}│{COLOR_RESET}")
    print(f"{COLOR_BORDER}└" + "─" * box_width + "┘" + f"{COLOR_RESET}")
    
    # Now Playing Info
    song_name = get_current_song_name()
    if len(song_name) > 42:
        song_name = song_name[:39] + "..."
        
    mode = get_mci_mode().upper() if is_playing else "STOPPED"
    if is_paused:
        mode = "PAUSED"
    
    pos = get_mci_position()
    length = get_mci_length()
    
    pos_str = format_time(pos)
    len_str = format_time(length)
    
    progress_bar = make_progress_bar(pos, length)
    volume_bar = make_volume_bar(volume)
    if muted:
        volume_bar = f"{COLOR_ERROR}[   MUTED  ]{COLOR_RESET}"
        
    print(f"  {COLOR_MUTED}STREAM_SOURCE{COLOR_RESET} : {COLOR_TITLE}{song_name}{COLOR_RESET}")
    print(f"  {COLOR_MUTED}PROCESS_STATE{COLOR_RESET} : {COLOR_ACCENT}{mode}{COLOR_RESET}")
    print(f"  {COLOR_MUTED}GAIN_LEVEL   {COLOR_RESET} : {volume}% {volume_bar}")
    print(f"  {COLOR_MUTED}BUFFER_INDEX {COLOR_RESET} : {pos_str}  {progress_bar}  {len_str}")
    
    # Download Info
    if download_status:
        dl_line = f"  {COLOR_MUTED}GET_REQUEST  {COLOR_RESET} : {COLOR_ACCENT}{download_status}{COLOR_RESET}"
        if download_info:
            dl_line += f" ({COLOR_MUTED}{download_info}{COLOR_RESET})"
        print(dl_line)
        
    print(f"  {COLOR_BORDER}──────────────────────────────────────────────────────────────{COLOR_RESET}")
    
    # Playlist Card
    playlist_border_top = "┌─ QUEUE_MANIFEST " + "─" * (box_width - 17) + "┐"
    print(f"{COLOR_BORDER}{playlist_border_top}{COLOR_RESET}")
    
    if not playlist:
        print(f"{COLOR_BORDER}│{COLOR_MUTED}  Queue manifest kosong.                                    {COLOR_BORDER}│{COLOR_RESET}")
    else:
        for idx, filepath in enumerate(playlist):
            name = os.path.basename(filepath)
            if len(name) > 38:
                name = name[:35] + "..."
            
            ext = os.path.splitext(filepath)[1][1:].upper()
            dur = get_track_duration(filepath)
            dur_str = format_time(dur) if dur > 0 else "--:--"
            
            marker = "▶ " if idx == current_track_index else "  "
            
            title_part = f"{marker}[{idx + 1}] {name}"
            info_part = f"[{ext} - {dur_str}]"
            
            space_needed = 56 - len(title_part) - len(info_part)
            if space_needed < 0:
                space_needed = 0
            
            row = f"  {title_part}{' ' * space_needed}  {info_part}"
            
            if idx == current_track_index:
                print(f"{COLOR_BORDER}│{COLOR_HIGHLIGHT_BG}{COLOR_HIGHLIGHT_FG}{row:<60}{COLOR_RESET}{COLOR_BORDER}│{COLOR_RESET}")
            else:
                print(f"{COLOR_BORDER}│{COLOR_MUTED}{row:<60}{COLOR_RESET}{COLOR_BORDER}│{COLOR_RESET}")
            
    print(f"{COLOR_BORDER}└" + "─" * box_width + "┘" + f"{COLOR_RESET}")
    
    # Status Alert Banner
    global status_msg
    if status_msg:
        color = COLOR_MUTED
        prefix = "[SYSTEM_INFO]"
        if status_type == "success":
            color = COLOR_SUCCESS
            prefix = "[STATUS_200_OK]"
        elif status_type == "error":
            color = COLOR_ERROR
            prefix = "[STATUS_500_ERR]"
            
        print(f"  {color}{prefix} {status_msg}{COLOR_RESET}")
        status_msg = "" # Reset after display
        
    print(f"  {COLOR_MUTED}(Ketik 'help' untuk panduan bantuan, tekan Enter untuk me-refresh){COLOR_RESET}\n")

def show_help():
    global status_msg, status_type
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{COLOR_TITLE}=================== PANDUAN BANTUAN PERINTAH ==================={COLOR_RESET}")
    print(f"  {COLOR_ACCENT}play{COLOR_RESET}          : Melanjutkan pemutaran musik atau memutar lagu pertama.")
    print(f"  {COLOR_ACCENT}play [indeks]{COLOR_RESET} : Memutar lagu berdasarkan nomor indeks playlist.")
    print(f"  {COLOR_ACCENT}pause{COLOR_RESET}         : Menjeda (pause) musik yang sedang diputar.")
    print(f"  {COLOR_ACCENT}resume{COLOR_RESET}        : Melanjutkan pemutaran musik setelah dijeda.")
    print(f"  {COLOR_ACCENT}stop{COLOR_RESET}          : Menghentikan pemutaran musik.")
    print(f"  {COLOR_ACCENT}next{COLOR_RESET}          : Memutar lagu berikutnya.")
    print(f"  {COLOR_ACCENT}prev{COLOR_RESET}          : Memutar lagu sebelumnya.")
    print(f"  {COLOR_ACCENT}volume [0-100] {COLOR_RESET}: Mengatur volume pemutar musik.")
    print(f"  {COLOR_ACCENT}mute{COLOR_RESET}          : Menonaktifkan atau mengaktifkan suara.")
    print(f"  {COLOR_ACCENT}download [url]{COLOR_RESET}: Mengunduh audio dari YouTube ke folder musik.")
    print(f"  {COLOR_ACCENT}list / ls{COLOR_RESET}     : Memperbarui tampilan playlist.")
    print(f"  {COLOR_ACCENT}exit / quit{COLOR_RESET}   : Keluar dari aplikasi.")
    print(f"{COLOR_TITLE}================================================================{COLOR_RESET}")
    input("\n  Tekan Enter untuk kembali...")

# --- MAIN EXECUTION ---
def main():
    global playlist, running, status_msg, status_type
    
    # Load playlist
    playlist = get_playlist()
    
    # Start background threads
    auto_play_thread = threading.Thread(target=auto_play_next_loop)
    auto_play_thread.daemon = True
    auto_play_thread.start()
    
    title_thread = threading.Thread(target=title_bar_update_loop)
    title_thread.daemon = True
    title_thread.start()
    
    # Initial status
    if playlist:
        status_msg = f"Ditemukan {len(playlist)} lagu. Ketik 'play 1' untuk memutar."
        status_type = "info"
    else:
        status_msg = "Folder musik kosong. Ketik 'download [URL]' untuk mengunduh lagu."
        status_type = "info"
    
    # Command loop
    while running:
        draw_ui()
        try:
            user_input = input(f"{COLOR_ACCENT}bitstream@user:~$ {COLOR_RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nKeluar...")
            break
            
        if not user_input:
            # Empty input acts as refresh
            continue
            
        parts = user_input.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        
        if cmd == "help":
            show_help()
        elif cmd in ["exit", "quit"]:
            break
        elif cmd == "play":
            if arg:
                try:
                    idx = int(arg) - 1
                    play_track(idx)
                except ValueError:
                    # Try playing by name match
                    matched_idx = -1
                    for i, filepath in enumerate(playlist):
                        if arg.lower() in os.path.basename(filepath).lower():
                            matched_idx = i
                            break
                    if matched_idx != -1:
                        play_track(matched_idx)
                    else:
                        status_msg = f"Indeks tidak valid atau lagu tidak ditemukan: {arg}"
                        status_type = "error"
            else:
                resume_track()
        elif cmd == "pause":
            pause_track()
        elif cmd in ["resume", "unpause"]:
            resume_track()
        elif cmd == "stop":
            stop_track()
        elif cmd == "next":
            next_track()
        elif cmd == "prev":
            prev_track()
        elif cmd in ["list", "ls"]:
            playlist = get_playlist()
            status_msg = f"Playlist diperbarui. Total: {len(playlist)} lagu."
            status_type = "info"
        elif cmd == "volume":
            try:
                vol = int(arg)
                set_volume(vol)
            except ValueError:
                status_msg = "Volume harus berupa angka antara 0-100."
                status_type = "error"
        elif cmd == "mute":
            toggle_mute()
        elif cmd == "download":
            if not arg:
                status_msg = "Masukkan URL YouTube. Contoh: download https://youtube.com/..."
                status_type = "error"
            else:
                start_download(arg)
        else:
            status_msg = f"Perintah tidak dikenal: '{cmd}'. Ketik 'help' untuk daftar perintah."
            status_type = "error"
            
    # Cleanup on exit
    running = False
    mci_send("stop my_music")
    mci_send("close my_music")
    print("exit(0) # Program terminated. Thank you for using BitStream Player!")

if __name__ == "__main__":
    main()
