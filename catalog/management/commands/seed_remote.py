# catalog/management/commands/seed_remote.py
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from catalog.management.commands.seed_demo import make_image
from catalog.models import Episode, Genre, Season, Title

G = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/"
REMOTE = [
    ("Big Buck Bunny (HLS)", "movie", 2008, 7.6, "Comedy", "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"),
    ("Big Buck Bunny", "movie", 2008, 7.6, "Comedy", G + "BigBuckBunny.mp4"),
    ("Sintel", "movie", 2010, 7.5, "Fantasy", G + "Sintel.mp4"),
    ("Tears of Steel", "movie", 2012, 7.0, "Sci-Fi", G + "TearsOfSteel.mp4"),
    ("Elephants Dream", "movie", 2006, 6.5, "Sci-Fi", G + "ElephantsDream.mp4"),
]


class Command(BaseCommand):
    help = "Add open-licensed titles that stream from remote URLs."

    def handle(self, *args, **opts):
        for i, (name, kind, year, rating, genre, url) in enumerate(REMOTE):
            slug = slugify(name)
            if Title.objects.filter(slug=slug).exists():
                continue
            t = Title(kind=kind, title=name, slug=slug, year=year, rating=rating,
                      overview="Open-licensed Blender Foundation film, streamed from a remote URL.",
                      remote_url=url)
            t.poster.save(f"{slug}.jpg", make_image(name, (300, 450), i / 6), save=False)
            t.backdrop.save(f"{slug}-bg.jpg", make_image(name, (1280, 720), i / 6), save=False)
            t.save()
            g, _ = Genre.objects.get_or_create(name=genre, defaults={"slug": slugify(genre)})
            t.genres.add(g)

        # a series whose episodes are all remote
        if not Title.objects.filter(slug="blender-shorts").exists():
            s = Title.objects.create(kind="series", title="Blender Shorts", slug="blender-shorts",
                                     year=2024, rating=7.0, overview="Remote-streamed episode test.")
            season = Season.objects.create(title=s, number=1)
            for n, (nm, *_, url) in enumerate(REMOTE[1:4], 1):
                Episode.objects.create(season=season, number=n, name=nm, remote_url=url)
        self.stdout.write(self.style.SUCCESS("Remote titles added."))