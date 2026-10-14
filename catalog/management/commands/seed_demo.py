# catalog/management/commands/seed_demo.py
import colorsys
import shutil
import subprocess
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from PIL import Image, ImageDraw

from catalog.models import Episode, Genre, Season, Title

DEMO = [
    ("Midnight Orbit", "movie", 2024, 8.7, ["Sci-Fi", "Drama"]),
    ("Dark Harbor", "movie", 2022, 7.9, ["Thriller"]),
    ("Echo Valley", "movie", 2023, 7.2, ["Drama"]),
    ("Neon Drift", "movie", 2021, 8.1, ["Action", "Sci-Fi"]),
    ("Paper Crown", "series", 2023, 8.4, ["Drama"]),
    ("Stellar Run", "series", 2024, 8.0, ["Sci-Fi", "Action"]),
    ("Glass Kingdom", "series", 2020, 7.6, ["Fantasy"]),
    ("Iron Tide", "series", 2022, 7.8, ["Action"]),
    ("Sakura Protocol", "anime", 2024, 8.9, ["Action", "Fantasy"]),
    ("Moonlit Ronin", "anime", 2023, 8.3, ["Drama", "Fantasy"]),
    ("Pixel Hearts", "anime", 2022, 7.5, ["Comedy"]),
    ("Skyforge Academy", "anime", 2021, 8.0, ["Action"]),
]


def make_image(text, size, hue):
    w, h = size
    img = Image.new("RGB", size)
    px = img.load()
    c1 = tuple(int(x * 255) for x in colorsys.hls_to_rgb(hue, 0.45, 0.7))
    c2 = tuple(int(x * 255) for x in colorsys.hls_to_rgb((hue + 0.15) % 1, 0.12, 0.6))
    for y in range(h):
        t = y / h
        row = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
        for x in range(w):
            px[x, y] = row
    d = ImageDraw.Draw(img)
    d.text((w * 0.06, h * 0.82), text, fill="white")
    buf = BytesIO()
    img.save(buf, "JPEG", quality=85)
    return ContentFile(buf.getvalue())


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class Command(BaseCommand):
    help = "Create demo titles, images and a test video (MP4 + HLS)."

    def add_arguments(self, parser):
        parser.add_argument("--video", help="Use your own .mp4 instead of a generated test clip")

    def handle(self, *args, **opts):
        media = Path(settings.MEDIA_ROOT)
        vdir = media / "video" / "demo"
        vdir.mkdir(parents=True, exist_ok=True)
        mp4 = vdir / "demo.mp4"
        hls_dir = vdir / "hls"
        m3u8 = hls_dir / "index.m3u8"

        if shutil.which("ffmpeg") is None:
            raise CommandError("ffmpeg not found. Install it and restart the terminal (see notes).")

        if opts["video"]:
            shutil.copy(opts["video"], mp4)
        elif not mp4.exists():
            self.stdout.write("Generating 30s test video...")
            run(["ffmpeg", "-y",
                 "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=24:duration=30",
                 "-f", "lavfi", "-i", "sine=frequency=440:duration=30",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "48",
                 "-c:a", "aac", "-shortest", "-movflags", "+faststart", str(mp4)])

        if not m3u8.exists():
            self.stdout.write("Creating HLS version...")
            hls_dir.mkdir(exist_ok=True)
            run(["ffmpeg", "-y", "-i", str(mp4), "-c", "copy",
                 "-hls_time", "4", "-hls_list_size", "0", "-f", "hls", str(m3u8)])

        mp4_name = "video/demo/demo.mp4"
        hls_name = "video/demo/hls/index.m3u8"

        for i, (name, kind, year, rating, genres) in enumerate(DEMO):
            slug = slugify(name)
            if Title.objects.filter(slug=slug).exists():
                continue
            hue = (i * 0.083) % 1
            t = Title(
                kind=kind, title=name, slug=slug, year=year, rating=rating,
                overview=f"{name} is a demo {kind} used to test the StreamFlix catalog, "
                         "search and playback. Replace it with real content later.",
                featured=(i == 0),
            )
            t.poster.save(f"{slug}.jpg", make_image(name, (300, 450), hue), save=False)
            t.backdrop.save(f"{slug}-bg.jpg", make_image(name, (1280, 720), hue), save=False)
            if kind == "movie":
                t.video.name = hls_name if i == 0 else mp4_name  # first movie plays via HLS
            t.save()
            for g in genres:
                obj, _ = Genre.objects.get_or_create(name=g, defaults={"slug": slugify(g)})
                t.genres.add(obj)

            if kind != "movie":
                for s in (1, 2):
                    season = Season.objects.create(title=t, number=s)
                    for e in (1, 2, 3):
                        Episode.objects.create(
                            season=season, number=e, name=f"Episode {e}",
                            video=mp4_name, duration=30,
                        )

        self.stdout.write(self.style.SUCCESS("Demo data ready. Run the server and open /"))