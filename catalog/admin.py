# catalog/admin.py
from django.contrib import admin
from .models import Episode, Genre, Season, Title


class SeasonInline(admin.TabularInline):
    model = Season
    extra = 0


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "year", "rating", "featured")
    list_filter = ("kind", "genres", "featured")
    search_fields = ("title",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [SeasonInline]


admin.site.register([Genre, Episode])