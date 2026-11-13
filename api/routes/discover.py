"""
Discovery: who to meet and what people are sharing.

GET /users/suggested  – a short, ranked list of people (not thousands):
    active creators first (songs, posts, stories), a nudge for your city and
    country, mutual friends and shared genres; there are always some people
    from other countries in the mix so everyone can meet everyone.

GET /posts/feed       – one timeline of posts, published songs and story clips.
    scope=friends  → your friends and you (Ana Sayfa)
    scope=everyone → everyone (Keşfet): your own posts too, your own songs not
    Cursor paging with `before` (created_at of the last item seen).
"""
import random
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from api.routes.songs import _song_dict
from api.routes.stories import _story_dict
from api.routes.wall import _load_posts_query, _post_dict, _mini_user
from api.routes.likes import like_info
from db.models import Activity, Friendship, FriendshipStatus, MusicStory, Song, StoryView, User, WallPost
from db.session import get_db
from services.auth_service import get_optional_user
from services.world import city_key

router = APIRouter(tags=["discover"])



def _friendships(db: Session, me: User):
    """{other_user_id: (status, friendship_id)} from my point of view, plus my accepted friend ids."""
    status_map, friends = {}, set()
    for f in db.query(Friendship).filter(
        (Friendship.requester_id == me.id) | (Friendship.addressee_id == me.id)
    ):
        other = f.addressee_id if f.requester_id == me.id else f.requester_id
        status = f.status.value
        if f.status == FriendshipStatus.pending and f.requester_id != me.id:
            status = "received_request"
        status_map[other] = (status, f.id)
        if f.status == FriendshipStatus.accepted:
            friends.add(other)
    return status_map, friends


def _accepted_friends_of(db: Session, ids):
    out = {}
    if not ids:
        return out
    for a, b in db.query(Friendship.requester_id, Friendship.addressee_id).filter(
        Friendship.status == FriendshipStatus.accepted,
        (Friendship.requester_id.in_(ids)) | (Friendship.addressee_id.in_(ids)),
    ):
        out.setdefault(a, set()).add(b)
        out.setdefault(b, set()).add(a)
    return out


AWAY_SLOTS = {1, 4, 7}     # in every 10: places 2, 5 and 8 go to other countries (~30%)


def _mix_world(ranked, my_country):
    """Keep the world in the mix all the way down: ~3 of every 10 from other countries."""
    home = [u for u in ranked if u.country_code == my_country]
    away = [u for u in ranked if u.country_code != my_country]
    out, h, a = [], 0, 0
    while h < len(home) or a < len(away):
        take_away = (len(out) % 10 in AWAY_SLOTS and a < len(away)) or h >= len(home)
        if take_away:
            out.append(away[a]); a += 1
        else:
            out.append(home[h]); h += 1
    return out


@router.get("/users/suggested")
def suggested_users(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    seed: int = Query(0, description="Same seed = same order, so paging is stable within a session"),
    me: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Everyone you could add, best matches first (paged with offset)."""
    now = datetime.utcnow()
    status_map, my_friends = _friendships(db, me) if me else ({}, set())

    # Activity per user: songs, posts, live stories
    song_stats = {uid: (n, last) for uid, n, last in db.query(
        Song.user_id, func.count(Song.id), func.max(Song.created_at)).group_by(Song.user_id)}
    post_stats = {uid: (n, last) for uid, n, last in db.query(
        WallPost.author_id, func.count(WallPost.id), func.max(WallPost.created_at)
    ).filter(WallPost.deleted_at.is_(None)).group_by(WallPost.author_id)}
    story_users = {uid for (uid,) in db.query(MusicStory.user_id).filter(MusicStory.expires_at > now).distinct()}

    def last_active(u):
        dates = [d for d in (song_stats.get(u.id, (0, None))[1], post_stats.get(u.id, (0, None))[1], u.updated_at, u.created_at) if d]
        return max(dates)

    users = db.query(User)
    if me:
        users = users.filter(User.id != me.id)
    pool = [u for u in users.all() if u.id not in my_friends]

    pool_friends = _accepted_friends_of(db, [u.id for u in pool])
    my_genres = set(me.favorite_genres or []) if me else set()
    my_city = city_key(me.city) if me and me.city else None
    my_country = me.country_code if me else None

    def score(u):
        songs = song_stats.get(u.id, (0, None))[0]
        posts = post_stats.get(u.id, (0, None))[0]
        days = (now - last_active(u)).total_seconds() / 86400
        s = min(songs, 10) * 1.5 + min(posts, 20) * 0.5 + (2 if u.id in story_users else 0)
        s += max(0.0, 7 - days) / 7 * 3                     # active this week: up to +3
        if my_country and u.country_code == my_country:
            s += 2
            if my_city and u.city_key == my_city:
                s += 3
        s += min(len(my_friends & pool_friends.get(u.id, set())), 10) * 2
        s += len(my_genres & set(u.favorite_genres or [])) * 1.5
        if not u.avatar_url:
            s -= 2                                          # half-finished accounts sink
        # a little variety per session, stable across pages of the same session
        return s + random.Random(f"{seed}:{u.id}").uniform(0, 2.5)

    ranked = sorted(pool, key=score, reverse=True)
    # Keep the world in the mix all the way down the list
    if my_country:
        ranked = _mix_world(ranked, my_country)
    total = len(ranked)
    picked = ranked[offset: offset + limit]

    # Latest public song per picked user
    ids = [u.id for u in picked]
    latest = {}
    if ids:
        rn = select(Song.id, func.row_number().over(partition_by=Song.user_id, order_by=Song.created_at.desc()).label("rn")) \
            .where(Song.user_id.in_(ids), Song.is_public == True).subquery()
        latest = {s.user_id: s for s in db.query(Song).join(rn, rn.c.id == Song.id).filter(rn.c.rn == 1)}

    items = []
    for u in picked:
        st, fid = status_map.get(u.id, (None, None))
        song = latest.get(u.id)
        items.append({
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name,
            "bio": u.bio,
            "avatar_url": u.avatar_url,
            "favorite_genres": list(u.favorite_genres or []),
            "country_code": u.country_code,
            "city": u.city,
            "same_country": bool(my_country and u.country_code == my_country),
            "same_city": bool(my_city and u.country_code == my_country and u.city_key == my_city),
            "friendship_status": st,
            "friendship_id": fid,
            "latest_song": _song_dict(song, include_user=False) if song else None,
            "song_count": song_stats.get(u.id, (0, None))[0],
            "post_count": post_stats.get(u.id, (0, None))[0],
            "has_story": u.id in story_users,
            "mutual_friend_count": len(my_friends & pool_friends.get(u.id, set())),
            "common_genre_count": len(my_genres & set(u.favorite_genres or [])),
            "last_active_at": last_active(u).isoformat(),
        })
    return {"items": items, "total": total, "has_more": offset + limit < total, "next_offset": offset + limit}


@router.get("/posts/feed")
def content_feed(
    scope: str = Query("everyone", pattern="^(friends|everyone)$"),
    before: Optional[datetime] = Query(None),
    limit: int = Query(20, ge=1, le=40),
    me: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    if scope == "friends":
        if not me:
            return {"items": [], "has_more": False, "next_before": None}
        _, friends = _friendships(db, me)
        authors = friends | {me.id}
    else:
        authors = None

    def window(q, col):
        if before is not None:
            q = q.filter(col < before)
        return q.order_by(col.desc()).limit(limit + 1)

    # Posts (status updates, shared songs, posts on friends' walls)
    # Everyone sees their own posts too, so what you just shared shows up in Keşfet
    pq = _load_posts_query(db).filter(WallPost.deleted_at.is_(None))
    if authors is not None:
        pq = pq.filter(WallPost.author_id.in_(authors))
    posts = window(pq, WallPost.created_at).all()

    # Published songs (skip ones the author also posted, to avoid doubles)
    sq = db.query(Song).options(joinedload(Song.user)).filter(Song.is_public == True)
    if authors is not None:
        sq = sq.filter(Song.user_id.in_(authors))
    elif me:
        sq = sq.filter(Song.user_id != me.id)
    songs = window(sq, Song.created_at).all()
    # a song its author also shared in a post shows once (as the post), on any page
    posted_songs = set()
    if songs:
        posted_songs = {(a, sid) for a, sid in db.query(WallPost.author_id, WallPost.song_id).filter(
            WallPost.song_id.in_([s.id for s in songs]), WallPost.deleted_at.is_(None))}

    # Story clips that are still live
    cq = db.query(MusicStory).options(joinedload(MusicStory.user), joinedload(MusicStory.song)) \
        .filter(MusicStory.expires_at > now)
    if authors is not None:
        cq = cq.filter(MusicStory.user_id.in_(authors))
    elif me:
        cq = cq.filter(MusicStory.user_id != me.id)
    clips = window(cq, MusicStory.created_at).all()
    seen = set()
    if me and clips:
        seen = {r[0] for r in db.query(StoryView.story_id).filter(
            StoryView.viewer_id == me.id, StoryView.story_id.in_([c.id for c in clips]))}

    # Likes and profile changes
    aq = db.query(Activity).options(joinedload(Activity.actor), joinedload(Activity.song).joinedload(Song.user))
    if authors is not None:
        aq = aq.filter(Activity.actor_id.in_(authors))
    elif me:
        aq = aq.filter(Activity.actor_id != me.id)
    acts = [a for a in window(aq, Activity.created_at).all()
            if a.kind != "like_song" or (a.song and a.song.is_public)]

    def act_item(a):
        base = {"id": f"act-{a.id}", "created_at": a.created_at.isoformat(), "user": _mini_user(a.actor)}
        if a.kind == "like_song":
            song = _song_dict(a.song, include_user=True)
            return {**base, "type": "like", "song": song}
        return {**base, "type": "profile", "kind": a.kind, "data": a.data or {}}

    merged = (
        [(p.created_at, {"type": "post", "id": f"post-{p.id}", "created_at": p.created_at.isoformat(),
                         "post": _post_dict(p, me)}) for p in posts]
        + [(s.created_at, {"type": "song", "id": f"song-{s.id}", "created_at": s.created_at.isoformat(),
                           "user": _mini_user(s.user), "song": _song_dict(s, include_user=False)})
           for s in songs if (s.user_id, s.id) not in posted_songs]
        + [(c.created_at, {"type": "clip", "id": f"clip-{c.id}", "created_at": c.created_at.isoformat(),
                           "user": _mini_user(c.user), "story": _story_dict(c, seen=c.id in seen)})
           for c in clips]
        + [(a.created_at, act_item(a)) for a in acts]
    )
    merged.sort(key=lambda x: x[0], reverse=True)
    page = merged[:limit]
    has_more = len(merged) > limit

    # Like counts on every song shown (posts, quotes, new songs, likes)
    songs_shown = []
    for _, it in page:
        if it["type"] in ("song", "like"):
            songs_shown.append(it["song"])
        elif it["type"] == "post":
            p = it["post"]
            if p.get("song"):
                songs_shown.append(p["song"])
            q = p.get("quote") or {}
            if q.get("type") == "song":
                songs_shown.append(q["song"])
            elif q.get("type") == "post" and q["post"].get("song"):
                songs_shown.append(q["post"]["song"])
    info = like_info(db, [x["id"] for x in songs_shown], me)
    for x in songs_shown:
        x["like_count"], x["liked"] = info.get(x["id"], (0, False))
    return {
        "items": [item for _, item in page],
        "has_more": has_more,
        "next_before": page[-1][0].isoformat() if has_more and page else None,
    }
