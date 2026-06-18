# BitStream Player v1.0

Pemutar musik berbasis Command Line Interface (CLI) minimalis dengan nuansa pemrograman (IT/Hacker) yang premium untuk Windows. Dibuat menggunakan Python dengan memanfaatkan Windows Media Control Interface (MCI) untuk pemutaran audio berkinerja tinggi secara native, dipadukan dengan pengunduh YouTube terintegrasi (`yt-dlp`) dan konverter audio MP3 otomatis (`FFmpeg`).

Aplikasi ini dirancang mengikuti pedoman desain antarmuka bersih (anti-slop), bebas dari em-dash (`—`), menggunakan visualizer progres yang rapi, dan tidak memblokir input Anda saat mengunduh lagu.

## Fitur Utama

- **IT/Hacker Themed UI**: Antarmuka terminal dengan prompt kustom `bitstream@user:~$`, respons ala log server (`STATUS_200_OK`, `STATUS_500_ERR`), dan label berorientasi sistem (`STREAM_SOURCE`, `PROCESS_STATE`, `GAIN_LEVEL`, `BUFFER_INDEX`).
- **Native Windows Playback**: Memutar file audio (`.mp3`, `.wav`, `.m4a`) tanpa menggunakan library audio pihak ketiga yang berat.
- **Asynchronous YouTube Downloader**: Mengunduh audio berkualitas tinggi langsung dari link YouTube secara asinkron tanpa menjeda musik yang sedang berputar.
- **Dynamic Console Title Bar**: Menampilkan status lagu (Judul, Durasi, Volume, Progress) di baris judul jendela Windows Command Prompt/PowerShell agar tidak mengganggu ketikan perintah Anda.
- **Auto-Play Next Track**: Secara otomatis memutar lagu berikutnya setelah lagu aktif selesai.
- **Audio Synthesizer Terbawa**: Membuat melodi instan untuk pengujian langsung tanpa perlu menaruh file audio terlebih dahulu.

## Persyaratan Sistem

- **Sistem Operasi**: Windows 10 atau Windows 11.
- **Runtime**: Python 3.11 atau lebih baru.
- **Dependensi**: `yt-dlp` (otomatis terpasang jika mengikuti langkah instalasi).

## Cara Instalasi & Menjalankan

1. **Unduh Dependensi**:
   Buka terminal di folder project ini dan jalankan perintah berikut untuk menginstal library pengunduh YouTube:
   ```bash
   python -m pip install --user -r requirements.txt
   ```

2. **Buat File Musik Contoh**:
   Agar langsung dapat dicoba tanpa harus mengunduh lagu terlebih dahulu, buat melodi contoh dengan menjalankan:
   ```bash
   python generate_sample.py
   ```
   Skrip ini akan mensintesis file audio 8 detik bernama `sample_melody.wav` di dalam folder `music/`.

3. **Jalankan Pemutar Musik**:
   Jalankan aplikasi utama dengan perintah:
   ```bash
   python player.py
   ```

## Panduan Perintah CLI

Setelah program berjalan, ketik perintah di bawah ini pada prompt `bitstream@user:~$ `:

| Perintah | Deskripsi | Contoh |
| :--- | :--- | :--- |
| `list` / `ls` | Menampilkan seluruh isi playlist terbaru | `list` |
| `play [indeks]` | Memutar lagu berdasarkan nomor indeks playlist | `play 1` |
| `play [nama]` | Memutar lagu berdasarkan pencocokan nama file | `play sample` |
| `play` | Melanjutkan lagu yang sedang dijeda (paused) | `play` |
| `pause` | Menjeda musik yang sedang diputar | `pause` |
| `resume` | Melanjutkan kembali lagu yang dijeda | `resume` |
| `stop` | Menghentikan pemutaran lagu sepenuhnya | `stop` |
| `next` | Memutar lagu berikutnya | `next` |
| `prev` | Memutar lagu sebelumnya | `prev` |
| `volume [0-100]` | Mengatur volume suara pemutar | `volume 50` |
| `mute` | Menonaktifkan / mengaktifkan suara | `mute` |
| `download [URL]` | Mengunduh audio dari YouTube ke folder musik | `download https://youtu.be/...` |
| `help` | Menampilkan panduan bantuan perintah | `help` |
| `exit` / `quit` | Keluar dari aplikasi dan menutup semua pemutar | `exit` |
