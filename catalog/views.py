# catalog/views.py
import json

from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector, TrigramSimilarity
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Title, WatchProgress, Episode

ROW_SIZE = 20


def home(request):
    rows = [
        ("Trending Now", Title.objects.order_by("-rating")[:ROW_SIZE]),
        ("Movies", Title.objects.filter(kind=Title.Kind.MOVIE)[:ROW_SIZE]),
        ("Series", Title.objects.filter(kind=Title.Kind.SERIES)[:ROW_SIZE]),
        ("Anime", Title.objects.filter(kind=Title.Kind.ANIME)[:ROW_SIZE]),
    ]
    if request.user.is_authenticated:
        watching = (
            WatchProgress.objects.filter(user=request.user)
            .select_related("title")[:ROW_SIZE]
        )
        rows.insert(0, ("Continue Watching", [w.title for w in watching]))

    hero = Title.objects.filter(featured=True).first() or Title.objects.first()
    return render(request, "catalog/home.html", {"hero": hero, "rows": rows})


def search_titles(q, limit=24):
    query = SearchQuery(q, config="simple")
    vector = SearchVector("title", weight="A", config="simple") + SearchVector(
        "overview", weight="C", config="simple"
    )
    return (
        Title.objects.annotate(
            rank=SearchRank(vector, query),
            sim=TrigramSimilarity("title", q),
        )
        .filter(Q(rank__gt=0.01) | Q(sim__gt=0.25))
        .order_by(F("rank").desc(), F("sim").desc())[:limit]
    )


def search(request):
    q = request.GET.get("q", "").strip()
    results = search_titles(q) if len(q) >= 2 else []
    if request.headers.get("Accept") == "application/json" or request.GET.get("json"):
        return JsonResponse(
            {
                "results": [
                    {
                        "title": t.title,
                        "kind": t.kind,
                        "year": t.year,
                        "url": t.get_absolute_url(),
                        "poster": t.poster.url if t.poster else "",
                    }
                    for t in results
                ]
            }
        )
    return render(request, "catalog/search.html", {"q": q, "results": results})


def detail(request, slug):
    title = get_object_or_404(
        Title.objects.prefetch_related("genres", "seasons__episodes"), slug=slug
    )
    episode = None
    if title.seasons.exists():
        eps = Episode.objects.filter(season__title=title).order_by("season__number", "number")
        ep_id = request.GET.get("ep")
        episode = (eps.filter(pk=ep_id).first() if ep_id and ep_id.isdigit() else None) or eps.first()

    source_url = (episode or title).stream_url
    start = 0
    if request.user.is_authenticated:
        p = WatchProgress.objects.filter(user=request.user, title=title, episode=episode).first()
        start = p.seconds if p else 0

    return render(request, "catalog/detail.html", {
        "title": title,
        "episode": episode,
        "source_url": source_url,
        "start": start,
    })


@require_POST
@login_required
def save_progress(request):
    data = json.loads(request.body)
    WatchProgress.objects.update_or_create(
        user=request.user,
        title_id=data["title"],
        episode_id=data.get("episode") or None,
        defaults={"seconds": max(0, int(data["seconds"]))},
    )
    return JsonResponse({"ok": True})