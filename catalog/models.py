# catalog/models.py
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.urls import reverse


class Genre(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Title(models.Model):
    class Kind(models.TextChoices):
        MOVIE = "movie", "Movie"
        SERIES = "series", "Series"
        ANIME = "anime", "Anime"

    kind = models.CharField(max_length=10, choices=Kind.choices, db_index=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    overview = models.TextField(blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    poster = models.ImageField(upload_to="posters/", blank=True)
    backdrop = models.ImageField(upload_to="backdrops/", blank=True)
    genres = models.ManyToManyField(Genre, related_name="titles", blank=True)
    video = models.FileField(upload_to="video/", blank=True)  # movies: HLS .m3u8 path or file
    featured = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    remote_url = models.URLField(max_length=500, blank=True, help_text="HLS (.m3u8) or MP4 URL")

    @property
    def stream_url(self):
        return self.remote_url or (self.video.url if self.video else "")

    class Meta:
        ordering = ["-created"]
        indexes = [
            GinIndex(name="title_trgm_idx", fields=["title"], opclasses=["gin_trgm_ops"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("catalog:detail", args=[self.slug])


class Season(models.Model):
    title = models.ForeignKey(Title, on_delete=models.CASCADE, related_name="seasons")
    number = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("title", "number")
        ordering = ["number"]

    def __str__(self):
        return f"{self.title} S{self.number}"


class Episode(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name="episodes")
    number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=200, blank=True)
    video = models.FileField(upload_to="video/", blank=True)   # blank=True is new
    remote_url = models.URLField(max_length=500, blank=True)   # new
    subtitles = models.FileField(upload_to="subs/", blank=True)
    duration = models.PositiveIntegerField(default=0, help_text="seconds")

    class Meta:
        unique_together = ("season", "number")
        ordering = ["number"]

    @property
    def stream_url(self):
        return self.remote_url or (self.video.url if self.video else "")

    def __str__(self):
        return f"{self.season} E{self.number}"


class WatchProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.ForeignKey(Title, on_delete=models.CASCADE)
    episode = models.ForeignKey(Episode, null=True, blank=True, on_delete=models.CASCADE)
    seconds = models.PositiveIntegerField(default=0)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "title", "episode")
        ordering = ["-updated"]


class Watchlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.ForeignKey(Title, on_delete=models.CASCADE)
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "title")